#!/usr/bin/env python

import os
import re
import subprocess
import zipfile

import envoy
import requests
import yaml

import utils

class TurnCommand(object):
    TEMP_COUNTRIES_FILENAME = 'countries.json'
    TEMP_CITIES_FILENAME = 'cities.json'
    TEMP_RIVERS_FILENAME = 'rivers.json'
    TEMP_LAKES_FILENAME = 'lakes.json'
    TEMP_NEIGHBORS_FILENAME = 'neighbors.json'
    TEMP_TOPOJSON_FILENAME = 'temp_topo.json'

    COUNTRIES_SHP_NAME = 'ne_10m_admin_0_countries'
    CITIES_SHP_NAME = 'ne_10m_populated_places_simple'
    RIVERS_SHP_NAME = 'ne_10m_rivers_lake_centerlines'
    LAKES_SHP_NAME = 'ne_10m_lakes'

    def __init__(self):
        self.args = None
        self.config = None

    def __call__(self, args):
        self.args = args

        with open(self.args.config, 'r') as f:
            self.config = yaml.load(f)

        for name, layer in self.config['layers'].items():
            if 'path' not in layer:
                print 'path missing for layer %s' % name
                return

            local_path = self.get_layer(layer['path'])


        # self.convert_countries()
        # self.convert_cities()
        # self.convert_rivers()
        # self.convert_lakes()
        # self.combine_layers()
        # self.merge_data()

    def add_argparser(self, root, parents):
        """
        Add arguments for this command.
        """
        parser = root.add_parser('turn', parents=parents)
        parser.set_defaults(func=self)

        parser.add_argument(
            dest='config', action='store',
            help='path to YAML configuration file.'
        )

        # parser.add_argument(
        #     dest='xmin', action='store',
        #     help='Minimum X value of bounding box.'
        # )

        # parser.add_argument(
        #     dest='ymin', action='store',
        #     help='Minimum Y value of bounding box.'
        # )

        # parser.add_argument(
        #     dest='xmax', action='store',
        #     help='Maximum X value of bounding box.'
        # )

        # parser.add_argument(
        #     dest='ymax', action='store',
        #     help='Maximum Y value of bounding box.'
        # )

        # parser.add_argument(
        #     metavar='DATA_FILE', nargs='+', dest='data_paths',
        #     help='Additional GeoJSON or CSV data to merge with output.'
        # )

        # parser.add_argument(
        #     '-c', '--country',
        #     dest='country', action='store',
        #     help='Country to include details for.'
        # )

        # parser.add_argument(
        #     '--scalerank',
        #     dest='scalerank', action='store', type=int, default=8,
        #     help='Scalerank for highlighted country (or all countries if none highlighted).'
        # )

        # parser.add_argument(
        #     '--neighbor-scalerank',
        #     dest='neighbor_scalerank', action='store', type=int, default=2,
        #     help='Scalerank for neighboring countries (if one is highlighted).'
        # )

        # parser.add_argument(
        #     '--river-scalerank',
        #     dest='river_scalerank', action='store', type=int, default=8,
        #     help='Scalerank for rivers.'
        # )

        return parser

    def get_layer(self, path):
        filename = path.split('/')[-1]
        local_path = os.path.join(utils.DATA_DIRECTORY, filename)
        filetype = os.path.splitext(filename)[1]

        if os.path.exists(local_path):
            pass
        elif re.match(r'^[a-zA-Z]+://', path):
            print 'Downloading %s...' % filename
            self.download_file(path, local_path)
        else:
            raise Exception('%s does not exist' % local_path)

        if filetype == '.zip':
            slug = os.path.splitext(filename)[0]
            output_path = os.path.join(utils.DATA_DIRECTORY, slug)
            if not os.path.exists(output_path):
                print 'Unzipping...'
                self.unzip_file(local_path, output_path)

            real_path = output_path
        else:
            real_path = local_path

        return real_path

    def download_file(self, url, local_path):
        response = requests.get(url, stream=True)

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

    def unzip_file(self, local_path, output_path):
        """
        Unzip a local file into a specified directory.
        """
        with zipfile.ZipFile(local_path, 'r') as z:
            z.extractall(output_path)

    def convert_countries(self):
        """
        Convert country data to GeoJSON.
        """
        path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_COUNTRIES_FILENAME)

        if os.path.exists(path):
            os.remove(path)

        r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s %(input_path)s' % {
            'xmin': self.args.xmin,
            'ymin': self.args.ymin,
            'xmax': self.args.xmax,
            'ymax': self.args.ymax,
            'output_path': path,
            'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.COUNTRIES_SHP_NAME, self.COUNTRIES_SHP_NAME))
        })

        if r.std_err:
            print r.std_err

    def convert_cities(self):
        """
        Convert city data to geojson, optionally focusing on a specific country.
        """
        if self.args.country:
            path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_CITIES_FILENAME)

            if os.path.exists(path):
                os.remove(path)

            # Focused country
            r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s -where %(where)s %(input_path)s' % {
                'xmin': self.args.xmin,
                'ymin': self.args.ymin,
                'xmax': self.args.xmax,
                'ymax': self.args.ymax,
                'output_path': path,
                'where': '"adm0name = \'%s\' AND scalerank < %i"' % (self.args.country, self.args.scalerank),
                'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.CITIES_SHP_NAME, self.CITIES_SHP_NAME)),
            })

            if r.std_err:
                print r.std_err

            path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_NEIGHBORS_FILENAME)

            if os.path.exists(path):
                os.remove(path)

            # Neighbors
            r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s -where %(where)s %(input_path)s' % {
                'xmin': self.args.xmin,
                'ymin': self.args.ymin,
                'xmax': self.args.xmax,
                'ymax': self.args.ymax,
                'output_path': path,
                'where': '"adm0name != \'%s\' AND scalerank < %i"' % (self.args.country, self.args.neighbor_scalerank),
                'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.CITIES_SHP_NAME, self.CITIES_SHP_NAME)),
            })

            if r.std_err:
                print r.std_err
        else:
            path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_CITIES_FILENAME)

            if os.path.exists(path):
                os.remove(path)

            r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s -where %(where)s %(input_path)s' % {
                'xmin': self.args.xmin,
                'ymin': self.args.ymin,
                'xmax': self.args.xmax,
                'ymax': self.args.ymax,
                'output_path': path,
                'where': '"scalerank < %i"' % self.args.scalerank,
                'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.CITIES_SHP_NAME, self.CITIES_SHP_NAME)),
            })

            if r.std_err:
                print r.std_err

    def convert_rivers(self):
        path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_RIVERS_FILENAME)

        if os.path.exists(path):
            os.remove(path)

        r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s -where %(where)s %(input_path)s' % {
            'xmin': self.args.xmin,
            'ymin': self.args.ymin,
            'xmax': self.args.xmax,
            'ymax': self.args.ymax,
            'output_path': path,
            'where': '"featurecla = \'River\' AND scalerank < %i"' % (self.args.river_scalerank),
            'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.RIVERS_SHP_NAME, self.RIVERS_SHP_NAME))
        })

        if r.std_err:
            print r.std_err

    def convert_lakes(self):
        path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_LAKES_FILENAME)

        if os.path.exists(path):
            os.remove(path)

        r = envoy.run('ogr2ogr -f GeoJSON -clipsrc %(xmin)s %(ymin)s %(xmax)s %(ymax)s %(output_path)s %(input_path)s' % {
            'xmin': self.args.xmin,
            'ymin': self.args.ymin,
            'xmax': self.args.xmax,
            'ymax': self.args.ymax,
            'output_path': path,
            'input_path': os.path.join(utils.DATA_DIRECTORY, '%s/%s.shp' % (self.LAKES_SHP_NAME, self.LAKES_SHP_NAME))
        })

        if r.std_err:
            print r.std_err

    def combine_layers(self):
        """
        Combine data layers into a single topojson file.
        """
        path = os.path.join(utils.DATA_DIRECTORY, self.TEMP_TOPOJSON_FILENAME)

        if os.path.exists(path):
            os.remove(path)

        paths = [
            os.path.join(utils.DATA_DIRECTORY, self.TEMP_COUNTRIES_FILENAME),
            os.path.join(utils.DATA_DIRECTORY, self.TEMP_CITIES_FILENAME),
        ]

        if self.args.country:
            paths.append(os.path.join(utils.DATA_DIRECTORY, self.TEMP_NEIGHBORS_FILENAME))

        r = envoy.run('topojson -o %(output_path)s --id-property NAME -p featurecla,city=name,country=NAME -- %(paths)s' % {
            'output_path': path,
            'paths': ' '.join(paths)
        })

        if r.std_err:
            print r.std_err

    def merge_data(self):
        path = 'output.json'

        if os.path.exists(path):
            os.remove(path)

        # No data to append
        if not self.args.data_paths:
            r = envoy.run('topojson -o %(output_path)s --bbox -p -- %(paths)s' % {
                'output_path': path,
                'paths': os.path.join(utils.DATA_DIRECTORY, self.TEMP_TOPOJSON_FILENAME)
            })

            if r.std_err:
                print r.std_err

            return

        data_paths = [
            os.path.join(utils.DATA_DIRECTORY, self.TEMP_TOPOJSON_FILENAME)
        ]

        data_paths.extend(self.args.data_paths)

        r = envoy.run('topojson -o %(output_path)s --bbox -p -- %(paths)s' % {
            'output_path': path,
            'paths': ' '.join(data_paths)
        })

        if r.std_err:
            print r.std_err
