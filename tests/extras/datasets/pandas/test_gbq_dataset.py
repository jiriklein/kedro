import pandas as pd
import pytest
from google.cloud.exceptions import NotFound
from pandas.testing import assert_frame_equal

from kedro.extras.datasets.pandas import GBQTableDataSet
from kedro.io.core import DataSetError

DATASET = "dataset"
TABLE_NAME = "table_name"
PROJECT = "project"


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def mock_bigquery_client(mocker):
    mocked = mocker.patch("google.cloud.bigquery.Client", autospec=True)
    return mocked


@pytest.fixture
def gbq_dataset(
    load_args, save_args, mock_bigquery_client
):  # pylint: disable=unused-argument
    return GBQTableDataSet(
        dataset=DATASET,
        table_name=TABLE_NAME,
        project=PROJECT,
        credentials=None,
        load_args=load_args,
        save_args=save_args,
    )


class TestGBQDataSet:
    def test_exists(self, mock_bigquery_client):
        """Test `exists` method invocation."""
        mock_bigquery_client.return_value.get_table.side_effect = [
            NotFound("NotFound"),
            "exists",
        ]

        data_set = GBQTableDataSet(DATASET, TABLE_NAME)
        assert not data_set.exists()
        assert data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, gbq_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert gbq_dataset._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, gbq_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert gbq_dataset._save_args[key] == value

    def test_load_missing_file(self, gbq_dataset, mocker):
        """Check the error when trying to load missing table."""
        pattern = r"Failed while loading data from data set GBQTableDataSet\(.*\)"
        mocked_read_gbq = mocker.patch(
            "kedro.extras.datasets.pandas.gbq_dataset.pd.read_gbq"
        )
        mocked_read_gbq.side_effect = ValueError
        with pytest.raises(DataSetError, match=pattern):
            gbq_dataset.load()

    @pytest.mark.parametrize("load_args", [{"location": "l1"}], indirect=True)
    @pytest.mark.parametrize("save_args", [{"location": "l2"}], indirect=True)
    def test_invalid_location(self, save_args, load_args):
        """Check the error when initializing instance if save_args and load_args
        `location` are different."""
        pattern = (
            r"`load_args\['location'\]` is different from `save_args\['location'\]`."
        )
        with pytest.raises(DataSetError, match=pattern):
            GBQTableDataSet(
                dataset=DATASET,
                table_name=TABLE_NAME,
                project=PROJECT,
                credentials=None,
                load_args=load_args,
                save_args=save_args,
            )

    @pytest.mark.parametrize("save_args", [{"option1": "value1"}], indirect=True)
    @pytest.mark.parametrize("load_args", [{"option2": "value2"}], indirect=True)
    def test_str_representation(self, gbq_dataset, save_args, load_args):
        """Test string representation of the data set instance."""
        str_repr = str(gbq_dataset)
        assert "GBQTableDataSet" in str_repr
        assert TABLE_NAME in str_repr
        assert DATASET in str_repr
        for k in save_args.keys():
            assert k in str_repr
        for k in load_args.keys():
            assert k in str_repr

    def test_save_load_data(self, gbq_dataset, dummy_dataframe, mocker):
        """Test saving and reloading the data set."""
        sql = f"select * from {DATASET}.{TABLE_NAME}"
        table_id = f"{DATASET}.{TABLE_NAME}"
        mocked_read_gbq = mocker.patch(
            "kedro.extras.datasets.pandas.gbq_dataset.pd.read_gbq"
        )
        mocked_read_gbq.return_value = dummy_dataframe
        mocked_df = mocker.Mock()

        gbq_dataset.save(mocked_df)
        loaded_data = gbq_dataset.load()

        mocked_df.to_gbq.assert_called_once_with(
            table_id, project_id=PROJECT, credentials=None, progress_bar=False
        )
        mocked_read_gbq.assert_called_once_with(
            project_id=PROJECT, credentials=None, query=sql
        )
        assert_frame_equal(dummy_dataframe, loaded_data)

    @pytest.mark.parametrize("load_args", [{"query": "Select 1"}], indirect=True)
    def test_read_gbq_with_query(self, gbq_dataset, dummy_dataframe, mocker, load_args):
        """Test loading data set with query in the argument."""
        mocked_read_gbq = mocker.patch(
            "kedro.extras.datasets.pandas.gbq_dataset.pd.read_gbq"
        )
        mocked_read_gbq.return_value = dummy_dataframe
        loaded_data = gbq_dataset.load()

        mocked_read_gbq.assert_called_once_with(
            project_id=PROJECT, credentials=None, query=load_args["query"]
        )

        assert_frame_equal(dummy_dataframe, loaded_data)

    @pytest.mark.parametrize(
        "dataset,table_name",
        [
            ("data set", TABLE_NAME),
            ("data;set", TABLE_NAME),
            (DATASET, "table name"),
            (DATASET, "table;name"),
        ],
    )
    def test_validation_of_dataset_and_table_name(self, dataset, table_name):
        pattern = "Neither white-space nor semicolon are allowed.*"
        with pytest.raises(DataSetError, match=pattern):
            GBQTableDataSet(dataset=dataset, table_name=table_name)

    def test_credentials_propagation(self, mocker):
        credentials = {"token": "my_token"}
        credentials_obj = "credentials"
        mocked_credentials = mocker.patch(
            "kedro.extras.datasets.pandas.gbq_dataset.Credentials",
            return_value=credentials_obj,
        )
        mocked_bigquery = mocker.patch(
            "kedro.extras.datasets.pandas.gbq_dataset.bigquery"
        )

        data_set = GBQTableDataSet(
            dataset=DATASET,
            table_name=TABLE_NAME,
            credentials=credentials,
            project=PROJECT,
        )

        assert data_set._credentials == credentials_obj
        mocked_credentials.assert_called_once_with(**credentials)
        mocked_bigquery.Client.assert_called_once_with(
            project=PROJECT, credentials=credentials_obj, location=None
        )
