import os
import pytest


@pytest.fixture(scope="session")
def spark():
    pytest.importorskip("pyspark")
    from pyspark.sql import SparkSession

    os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")
    session = (
        SparkSession.builder.master("local[2]")
        .appName("NordicWeatherRiskTests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
