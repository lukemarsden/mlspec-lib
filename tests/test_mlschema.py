# pylint: disable=protected-access,missing-function-docstring, missing-class-docstring, missing-module-docstring
# -*- coding: utf-8 -*-
import unittest
from ruamel.yaml.scanner import ScannerError

import marshmallow
from marshmallow import fields, Schema, ValidationError

from mlspeclib.mlschema import MLSchema
from mlspeclib.helpers import convert_yaml_to_dict
from tests.sample_schemas import SampleSchema
from tests.sample_submissions import SampleSubmissions

class SchemaTestSuite(unittest.TestCase):
    """MLSchema test cases."""

    def test_create_valid_schema(self):
        instantiated_schema, _ = return_base_schema_and_submission()
        assert len(instantiated_schema.declared_fields) == 5

    def test_create_base_object(self):
        instantiated_schema, yaml_submission = return_base_schema_and_submission()
        instantiated_object = instantiated_schema.load(yaml_submission)
        assert instantiated_object['run_date'].isoformat() == '1970-01-01T00:00:00'

    def test_enter_schema_with_invalid_yaml(self):
        with self.assertRaises(ScannerError):
            MLSchema.create(SampleSchema.TEST.INVALID_YAML)

    def test_convert_dicts_to_sub_schema(self):
        class UserSchema(Schema):
            name = fields.String(required=True)
            email = fields.Email(required=True)


        class BlogSchema(Schema):
            title = fields.String(required=True)
            year = fields.Int(required=True)
            author = fields.Nested(UserSchema, required=True)

        marshmallow.class_registry.register("blog_author", \
                                            UserSchema)
        marshmallow.class_registry.register("blog", \
                                            BlogSchema)

        sub_schema_string = """
title: "Something Completely Different"
year: 1970
author:
    name: "Monty"
    email: "monty@python.org"
"""
        full_schema_data = convert_yaml_to_dict(sub_schema_string)
        full_schema_loaded = MLSchema.check_for_nested_schemas_and_convert(BlogSchema, \
                                                                           'blog', \
                                                                           full_schema_data)

        self.assertTrue(full_schema_loaded['title'] == full_schema_data['title'])
        self.assertTrue(full_schema_loaded['author']['name'] == full_schema_data['author']['name'])

        missing_author_name_data = convert_yaml_to_dict(sub_schema_string)
        missing_author_name_data['author'].pop('name', None)

        with self.assertRaises(ValidationError):
            MLSchema.check_for_nested_schemas_and_convert(BlogSchema, \
                                                          'blog', \
                                                          missing_author_name_data)

        missing_year_data = convert_yaml_to_dict(sub_schema_string)
        missing_year_data.pop('year', None)

        with self.assertRaises(ValidationError):
            missing_year_loaded = MLSchema.check_for_nested_schemas_and_convert(BlogSchema, \
                                                                                'blog', \
                                                                                missing_year_data)
            BlogSchema().load(missing_year_loaded)

    def test_create_nested_schema(self):
        connection_text = """
mlspec_version:
    # Identifies the version of this schema
    meta: 0.0.1
mlspec_schema_type:
    # Identifies the type of this schema
    meta: datapath
# Connection to datapath
schema_version:
    type: semver
    required: True
schema_type:
    type: string
    required: True
connection:
  type: nested
  schema:
    # URI for the location of the data store
    endpoint:
        type: URI
        required: True
one_more_field:
    type: String
    required: True"""

        nested_schema = MLSchema.create(connection_text, "0_0_1_datapath")

        connection_submission = """
schema_version: 0.0.1
schema_type: datapath
connection:
    endpoint: S3://mybucket/puppy.jpg
one_more_field: foobaz
"""
        connection_submission_dict = convert_yaml_to_dict(connection_submission)
        nested_object = nested_schema.load(connection_submission)
        self.assertTrue(nested_object['connection']['endpoint'] == \
                        connection_submission_dict['connection']['endpoint'])
        self.assertTrue(nested_object['one_more_field'] == \
                        connection_submission_dict['one_more_field'])

        nested_missing_endpoint_dict = convert_yaml_to_dict(connection_submission)
        nested_missing_endpoint_dict['connection'].pop('endpoint', None)

        with self.assertRaises(ValidationError):
            missing_nested_object = nested_schema.load(nested_missing_endpoint_dict)

        missing_extra_dict = convert_yaml_to_dict(connection_submission)
        missing_extra_dict.pop('one_more_field', None)

        with self.assertRaises(ValidationError):
            missing_object = nested_schema.load(missing_extra_dict)

    def test_merge_two_dicts_with_invalid_base(self):
        # Should not work - trying to instantiate a schema with a base_type
        # but the base_type has not been registered
        with self.assertRaises(KeyError) as context:
            MLSchema.create(SampleSchema.SCHEMAS.DATAPATH)

        self.assertTrue("has not been registered as a schema and " \
                            "cannot be used as a base schema." in str(context.exception))

    def test_merge_two_dicts_with_valid_base(self):
        base_schema = MLSchema.create(SampleSchema.SCHEMAS.BASE)
        base_object = base_schema.load(SampleSubmissions.FULL_SUBMISSIONS.BASE)
        datapath_schema = MLSchema.create(SampleSchema.SCHEMAS.DATAPATH)
        datapath_object = datapath_schema.load(SampleSubmissions.FULL_SUBMISSIONS.DATAPATH)

        # Should not work - BASE did not merge with DATAPATH
        with self.assertRaises(KeyError):
            base_object['data_store'] == 'NULL_STRING_SHOULD_NOT_WORK' #pylint: disable=pointless-statement

        self.assertTrue(base_object['run_id'] == 'uuid')

        # Should work - DATAPATH inherited from BASE
        self.assertTrue(datapath_object['data_store'] == 'string')
        self.assertTrue(datapath_object['run_id'] == 'uuid')

    @unittest.skip("NYI")
    def test_create_schema_with_invalid_base(self):
        pass

"""
    def test_enter_schema_with_invalid_enum(self):
        ml_schema = MLSchema()
        with self.assertRaises(KeyError) as context:
            ml_schema['xxxx'] = SampleSchema.SCHEMAS.BASE

        self.assertTrue("is not an enum from mlspeclib.schemacatalog.SchemaTypes"\
                                                            in str(context.exception))

    def test_entering_string_and_converting_to_yaml(self):
        ml_schema = MLSchema()
        ml_schema[SchemaTypes.BASE] = SampleSchema.SCHEMAS.BASE
        self.assertIsInstance(ml_schema[SchemaTypes.BASE], dict)
        self.assertTrue(ml_schema[SchemaTypes.BASE]['schema_version']['type'] == 'semver')

    def test_entering_yaml_and_not_converting(self):
        ml_schema = MLSchema()
        ml_schema[SchemaTypes.BASE] = SampleSchema.SCHEMAS.BASE
        self.assertIsInstance(ml_schema[SchemaTypes.BASE], dict)
        self.assertTrue(ml_schema[SchemaTypes.BASE]['schema_version']['type'] == 'semver')

"""

def return_base_schema_and_submission():
    instantiated_schema = MLSchema.create(SampleSchema.SCHEMAS.BASE)
    yaml_submission = convert_yaml_to_dict(SampleSubmissions.FULL_SUBMISSIONS.BASE)
    return instantiated_schema, yaml_submission

if __name__ == '__main__':
    unittest.main()