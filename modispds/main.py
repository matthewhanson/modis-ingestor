import sys
import time
import os
import datetime
import logging
import argparse
from modispds.cmr import query, download_granule
from modispds.pds import push_to_s3, s3_list, make_index, make_scene_list
import gippy
from modispds.version import __version__
from modispds.products import products

logger = logging.getLogger('modispds')

# default product
_PRODUCT = 'MCD43A4.006'

# environment variables
bucket = os.getenv('BUCKET', 'modis-pds')


def ingest(date1, date2, product=_PRODUCT, outdir=''):
    """ Ingest all granules between two dates """
    granules = query(date1, date2, product=product)

    metadata = []
    for gran in granules:
        metadata.append(ingest_granule(gran, outdir=outdir))
    fname = make_scene_list(metadata)


def ingest_granule(gran, outdir='', prefix=''):
    """ Fetch granule, process, and push to s3 """
    url = gran['Granule']['OnlineAccessURLs']['OnlineAccessURL']['URL']
    bname = os.path.basename(url)
    gid = os.path.splitext(bname)[0]
    start_time = time.time()
    logger.info('Processing tile %s' % gid)

    # create geotiffs
    logger.info('Downloading granule %s' % gid)
    fnames = download_granule(gran, outdir=outdir)

    logger.info('Converting to GeoTIFFs')
    files = convert_to_geotiff(fnames[0])

    # create index.html
    files.extend(fnames[2:])
    index_fname = make_index(fnames[1], bname, files)
    files.append(index_fname)
    files.append(fnames[1])

    # upload files to s3
    path = get_s3_path(bname, prefix=prefix)
    s3fnames = []
    for f in files:
        s3fnames.append(push_to_s3(f, bucket, path))
        # cleanup
        os.remove(f)

    # cleanup original download
    os.remove(fnames[0])

    logger.info('Completed processing granule %s in : %ss' % (gid, time.time() - start_time))
    return {
        'gid': gid,
        'date': get_date(gid),
        'download_url': os.path.join('https://%s.s3.amazonaws.com', path, 'index.html')
    }


def convert_to_geotiff(hdf, outdir=''):
    bname = os.path.basename(hdf)
    parts = bname.split('.')
    product = parts[0] + '.' + parts[3]
    bandnames = products[product]['bandnames']
    overviews = products[product]['overviews']
    file_names = []
    img = gippy.GeoImage(hdf, True)
    opts = {'COMPRESS': 'DEFLATE', 'PREDICTOR': '2', 'TILED': 'YES', 'BLOCKXSIZE': '512', 'BLOCKYSIZE': '512'}
    # save each band as a TIF
    for i, band in enumerate(img):
        fname = os.path.join(outdir, bname.replace('.hdf', '') + '_' + bandnames[i] + '.TIF')
        logger.info('Writing %s' % fname)
        imgout = img.select([i+1]).save(fname, options=opts)
        file_names.append(fname)
        # add overview as separate file
        if overviews[i]:
            imgout = None
            imgout = gippy.GeoImage(fname, False)
            imgout.add_overviews()
            file_names.append(fname + '.ovr')

    return file_names


def granule_exists(granule, prefix=''):
    """ Check if the granule exists already on AWS """
    s3path = os.path.join('s3://%s' % bucket, get_s3_path(granule, prefix=prefix))
    urls = s3_list(s3path)
    return True if len(urls) == 18 else False


def get_s3_path(gid, prefix=''):
    """ Generate complete path in an S3 bucket (not including bucket name) """
    parts = gid.split('.')
    prod = '%s.%s' % (parts[0], parts[3])
    tile = parts[2].replace('h', '').replace('v', os.path.sep)
    date = parts[1].replace('A', '')
    path = os.path.join(prod, tile, date)
    if prefix != '':
        path = os.path.join(prefix, path)
    return path


def get_date(gid):
    """ Get date from granule ID """
    d = gid.split('.')[1].replace('A', '')
    return datetime.datetime.strptime(d, '%Y%j')


def parse_args(args):
    """ Parse arguments for the NDWI algorithm """
    desc = 'MODIS Public Dataset Utility (v%s)' % __version__
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=dhf)
    parser.add_argument('--version', help='Print version and exit', action='version', version=__version__)

    parser.add_argument('start_date', help='First date')
    parser.add_argument('end_date', help='End date')
    parser.add_argument('-p', '--product', default=_PRODUCT)

    return parser.parse_args(args)


def cli():
    args = parse_args(sys.argv[1:])
    ingest(args.start_date, args.end_date, product=args.product)


if __name__ == "__main__":
    cli()
