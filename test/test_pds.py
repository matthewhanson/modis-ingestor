import os
import unittest
from modispds.pds import push_to_s3, exists, s3_list, del_from_s3, make_index


class TestPDS(unittest.TestCase):
    """ Test utiltiies for publishing data on AWS PDS """

    def test_make_index(self):
        """ Create HTML index of some files """
        fname = make_index('thumbnail.jpg', 'product', ['file1.tif', 'file2.tif'])
        self.assertTrue(os.path.exists(fname))

    def test_exists(self):
        """ Check for existence of fake object """
        self.assertFalse(exists('s3://modis-pds/nothinghere'))

    def test_list_nothing(self):
        """ Get list of objects under a non-existent path on S3 """
        urls = s3_list('s3://modis-pds/nothinghere')
        self.assertEqual(len(urls), 0)

    def test_list(self):
        """ Get list of objects under a path on S3 """
        url = push_to_s3(__file__, 'modis-pds', 'testing/unittests')
        fnames = s3_list(os.path.dirname(url))
        self.assertEqual(len(fnames), 1)
        self.assertEqual(fnames[0], url)
        del_from_s3(url)

    def test_push_to_s3(self):
        """ Push file to S3 """
        url = push_to_s3(__file__, 'modis-pds', 'testing')
        self.assertTrue(exists(url))
        del_from_s3(url)