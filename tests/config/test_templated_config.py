from pathlib import Path
from typing import Dict

import pytest
import yaml

from kedro.config import TemplatedConfigLoader
from kedro.config.templated_config import _format_object


def _write_yaml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


@pytest.fixture
def conf_paths(tmp_path):
    return [str(tmp_path / "base"), str(tmp_path / "local")]


@pytest.fixture
def param_config():
    return {
        "boats": {
            "type": "${boat_data_type}",
            "filepath": "${s3_bucket}/${raw_data_folder}/${boat_file_name}",
            "columns": {
                "id": "${string_type}",
                "name": "${string_type}",
                "top_speed": "${float_type}",
            },
            "rows": 5,
            "users": ["fred", "${write_only_user}"],
        }
    }


@pytest.fixture
def template_config():
    return {
        "s3_bucket": "s3a://boat-and-car-bucket",
        "raw_data_folder": "01_raw",
        "boat_file_name": "boats.csv",
        "boat_data_type": "SparkDataSet",
        "string_type": "VARCHAR",
        "float_type": "FLOAT",
        "write_only_user": "ron",
    }


@pytest.fixture
def catalog_with_jinja2_syntax(tmp_path):
    filepath = tmp_path / "base" / "catalog.yml"

    catalog = """
{% for speed in ['fast', 'slow'] %}
{{ speed }}-trains:
    type: MemoryDataSet

{{ speed }}-cars:
    type: pandas.CSVDataSet
    filepath: ${s3_bucket}/{{ speed }}-cars.csv
    save_args:
        index: true

{% endfor %}
"""

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(catalog)


@pytest.fixture
def proj_catalog_param(tmp_path, param_config):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config)


@pytest.fixture
def proj_catalog_globals(tmp_path, template_config):
    global_yml = tmp_path / "base" / "globals.yml"
    _write_yaml(global_yml, template_config)


@pytest.fixture
def normal_config_advanced():
    return {
        "planes": {
            "type": "SparkJDBCDataSet",
            "postgres_credentials": {"user": "Fakeuser", "password": "F@keP@55word"},
            "batch_size": 10000,
            "need_permission": True,
            "secret_tables": ["models", "pilots", "engines"],
        }
    }


@pytest.fixture
def proj_catalog_advanced(tmp_path, normal_config_advanced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, normal_config_advanced)


@pytest.fixture
def param_config_advanced():
    return {
        "planes": {
            "type": "${plane_data_type}",
            "postgres_credentials": "${credentials}",
            "batch_size": "${batch_size}",
            "need_permission": "${permission_param}",
            "secret_tables": "${secret_table_list}",
        }
    }


@pytest.fixture
def template_config_advanced():
    return {
        "plane_data_type": "SparkJDBCDataSet",
        "credentials": {"user": "Fakeuser", "password": "F@keP@55word"},
        "batch_size": 10000,
        "permission_param": True,
        "secret_table_list": ["models", "pilots", "engines"],
    }


@pytest.fixture
def proj_catalog_param_w_vals_advanced(tmp_path, param_config_advanced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_advanced)


@pytest.fixture
def param_config_mixed():
    return {
        "boats": {
            "type": "${boat_data_type}",
            "filepath": "${s3_bucket}/${raw_data_folder}/${boat_file_name}",
            "columns": {
                "id": "${string_type}",
                "name": "${string_type}",
                "top_speed": "${float_type}",
            },
            "users": ["fred", "${USER}"],
        }
    }


@pytest.fixture
def get_environ():
    return {"USER": "ron"}


@pytest.fixture
def proj_catalog_param_mixed(tmp_path, param_config_mixed):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_mixed)


@pytest.fixture
def param_config_namespaced():
    return {
        "boats": {
            "type": "${global.boat_data_type}",
            "filepath": "${global.s3_bucket}/${global.raw_data_folder}/${global.boat_file_name}",
            "columns": {
                "id": "${global.string_type}",
                "name": "${global.string_type}",
                "top_speed": "${global.float_type}",
            },
            "users": ["fred", "${env.USER}"],
        }
    }


@pytest.fixture
def proj_catalog_param_namespaced(tmp_path, param_config_namespaced):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_namespaced)


@pytest.fixture
def param_config_exceptional():
    return {"postcode": "${area}${district} ${sector}${unit}"}


@pytest.fixture
def template_config_exceptional():
    return {"area": "NW", "district": 10, "sector": 2, "unit": "JK"}


@pytest.fixture
def proj_catalog_param_w_vals_exceptional(tmp_path, param_config_exceptional):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_exceptional)


@pytest.fixture
def param_config_with_default():
    return {"boats": {"users": ["fred", "${write_only_user|ron}"]}}


@pytest.fixture
def proj_catalog_param_with_default(tmp_path, param_config_with_default):
    proj_catalog = tmp_path / "base" / "catalog.yml"
    _write_yaml(proj_catalog, param_config_with_default)


class TestTemplatedConfigLoader:
    @pytest.mark.usefixtures("proj_catalog_param")
    def test_catalog_parameterized_w_dict(self, tmp_path, conf_paths, template_config):
        """Test parameterized config with input from dictionary with values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths, globals_dict=template_config).get(
            "catalog*.yml"
        )

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param", "proj_catalog_globals")
    def test_catalog_parameterized_w_globals(self, tmp_path, conf_paths):
        """Test parameterized config with globals yaml file"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths, globals_pattern="*globals.yml").get(
            "catalog*.yml"
        )

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param")
    def test_catalog_parameterized_no_params_no_default(self, tmp_path, conf_paths):
        """Test parameterized config without input"""
        (tmp_path / "local").mkdir(exist_ok=True)

        with pytest.raises(ValueError, match="Failed to format pattern"):
            TemplatedConfigLoader(conf_paths).get("catalog*.yml")

    @pytest.mark.usefixtures("proj_catalog_param_with_default")
    def test_catalog_parameterized_empty_params_with_default(
        self, tmp_path, conf_paths
    ):
        """Test parameterized config with empty globals dictionary"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(conf_paths, globals_dict={}).get("catalog*.yml")

        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_advanced")
    def test_catalog_advanced(self, tmp_path, conf_paths, normal_config_advanced):
        """Test whether it responds well to advanced yaml values
        (i.e. nested dicts, booleans, lists, etc.)"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=normal_config_advanced
        ).get("catalog*.yml")

        assert catalog["planes"]["type"] == "SparkJDBCDataSet"
        assert catalog["planes"]["postgres_credentials"]["user"] == "Fakeuser"
        assert catalog["planes"]["postgres_credentials"]["password"] == "F@keP@55word"
        assert catalog["planes"]["batch_size"] == 10000
        assert catalog["planes"]["need_permission"]
        assert catalog["planes"]["secret_tables"] == ["models", "pilots", "engines"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_advanced")
    def test_catalog_parameterized_advanced(
        self, tmp_path, conf_paths, template_config_advanced
    ):
        """Test advanced templating (i.e. nested dicts, booleans, lists, etc.)"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=template_config_advanced
        ).get("catalog*.yml")

        assert catalog["planes"]["type"] == "SparkJDBCDataSet"
        assert catalog["planes"]["postgres_credentials"]["user"] == "Fakeuser"
        assert catalog["planes"]["postgres_credentials"]["password"] == "F@keP@55word"
        assert catalog["planes"]["batch_size"] == 10000
        assert catalog["planes"]["need_permission"]
        assert catalog["planes"]["secret_tables"] == ["models", "pilots", "engines"]

    @pytest.mark.usefixtures("proj_catalog_param_mixed", "proj_catalog_globals")
    def test_catalog_parameterized_w_dict_mixed(
        self, tmp_path, conf_paths, get_environ
    ):
        """Test parameterized config with input from dictionary with values
        and globals.yml"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_pattern="*globals.yml", globals_dict=get_environ
        ).get("catalog*.yml")

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_namespaced")
    def test_catalog_parameterized_w_dict_namespaced(
        self, tmp_path, conf_paths, template_config, get_environ
    ):
        """Test parameterized config with namespacing in the template values"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict={"global": template_config, "env": get_environ}
        ).get("catalog*.yml")

        assert catalog["boats"]["type"] == "SparkDataSet"
        assert (
            catalog["boats"]["filepath"] == "s3a://boat-and-car-bucket/01_raw/boats.csv"
        )
        assert catalog["boats"]["columns"]["id"] == "VARCHAR"
        assert catalog["boats"]["columns"]["name"] == "VARCHAR"
        assert catalog["boats"]["columns"]["top_speed"] == "FLOAT"
        assert catalog["boats"]["users"] == ["fred", "ron"]

    @pytest.mark.usefixtures("proj_catalog_param_w_vals_exceptional")
    def test_catalog_parameterized_exceptional(
        self, tmp_path, conf_paths, template_config_exceptional
    ):
        """Test templating with mixed type replacement values going into one string"""
        (tmp_path / "local").mkdir(exist_ok=True)

        catalog = TemplatedConfigLoader(
            conf_paths, globals_dict=template_config_exceptional
        ).get("catalog*.yml")

        assert catalog["postcode"] == "NW10 2JK"

    @pytest.mark.usefixtures("catalog_with_jinja2_syntax")
    def test_catalog_with_jinja2_syntax(self, tmp_path, conf_paths, template_config):
        (tmp_path / "local").mkdir(exist_ok=True)
        catalog = TemplatedConfigLoader(conf_paths, globals_dict=template_config).get(
            "catalog*.yml"
        )
        expected_catalog = {
            "fast-trains": {"type": "MemoryDataSet"},
            "fast-cars": {
                "type": "pandas.CSVDataSet",
                "filepath": "s3a://boat-and-car-bucket/fast-cars.csv",
                "save_args": {"index": True},
            },
            "slow-trains": {"type": "MemoryDataSet"},
            "slow-cars": {
                "type": "pandas.CSVDataSet",
                "filepath": "s3a://boat-and-car-bucket/slow-cars.csv",
                "save_args": {"index": True},
            },
        }
        assert catalog == expected_catalog


class TestFormatObject:
    @pytest.mark.parametrize(
        "val, format_dict, expected",
        [
            # No templating
            ("a", {}, "a"),
            ("a", {"a": "b"}, "a"),
            ("{a}", {"a": "b"}, "{a}"),
            ("ab.c-d", {}, "ab.c-d"),
            # Simple templating
            ("${a}", {"a": "b"}, "b"),
            ("${a}", {"a": True}, True),
            ("${a}", {"a": 123}, 123),
            ("${a}", {"a": {"b": "c"}}, {"b": "c"}),
            ("${a}", {"a": ["b", "c"]}, ["b", "c"]),
            ("X${a}", {"a": "b"}, "Xb"),
            ("X${a}", {"a": True}, "XTrue"),
            ("X${a}", {"a": {"b": "c"}}, "X{'b': 'c'}"),
            ("X${a}", {"a": ["b", "c"]}, "X['b', 'c']"),
            # Nested templating
            ("${a.b}", {"a": {"b": "c"}}, "c"),
            ("${a.b}", {"a": {"b": True}}, True),
            ("X${a.b}", {"a": {"b": True}}, "XTrue"),
            # Templating with defaults
            ("${a|D}", {"a": "b"}, "b"),
            ("${a|D}", {}, "D"),
            ("${a|}", {}, ""),
            ("${a.b|D}", {"a": {"b": "c"}}, "c"),
            ("${a|D}", {"a": True}, True),
            ("X${a|D}Y", {"a": True}, "XTrueY"),
            ("X${a|D1}Y${b|D2}", {}, "XD1YD2"),
            # Lists
            (["a"], {"a": "A"}, ["a"]),
            (["${a}", "X${a}"], {"a": "A"}, ["A", "XA"]),
            (["${b|D}"], {"a": "A"}, ["D"]),
            (["${b|abcDEF_.<>/@$%^&!}"], {"a": "A"}, ["abcDEF_.<>/@$%^&!"]),
            # Dicts
            ({"key": "${a}"}, {"a": "A"}, {"key": "A"}),
            ({"${a}": "value"}, {"a": "A"}, {"A": "value"}),
            ({"${a|D}": "value"}, {}, {"D": "value"}),
        ],
    )
    def test_simple_replace(self, val, format_dict, expected):
        assert _format_object(val, format_dict) == expected

    @pytest.mark.parametrize(
        "val, format_dict, expected_error_message",
        [
            ("${a}", {}, r"Failed to format pattern '\$\{a\}': no config"),
            (
                "${a.b}",
                {"a": "xxx"},
                r"Failed to format pattern '\$\{a\.b\}': no config",
            ),
            (
                {"${a}": "VALUE"},
                {"a": True},
                r"When formatting '\$\{a\}' key, only string values can be used. 'True' found",
            ),
        ],
    )
    def test_raises_error(self, val, format_dict, expected_error_message):
        with pytest.raises(ValueError, match=expected_error_message):
            _format_object(val, format_dict)
