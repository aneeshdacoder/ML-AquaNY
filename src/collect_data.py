import requests
import pandas
import os
from pathlib import Path
import time

STATE_CODE = "36"

START_DATE = "2024-01-01"
END_DATE = "2025-01-01"

PARAMETER_CODE = "00060" #discharge. just to test b/c it gets really big

OUTPUT_FILE = Path("data/raw/usgs_streamflow_2024.csv")

URL = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items"

PAGE_SIZE = 10000

def get_page(url, params):

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    return response.json()

def download_data():
    params = {
        "f": "json",
        "state_code": STATE_CODE,
        "parameter_code": PARAMETER_CODE,
        "datetime": f"{START_DATE}/{END_DATE}",
        "api_key": os.getenv("API_KEY"),
        "limit": PAGE_SIZE
    }

    all_features = []

    page_number = 1
    url = URL

    print("start")

    while True:
        print(f"\n page number:{page_number}")

        data = get_page(url, params)

        features = data.get("features", [])

        print(f"records gotten {len(features)}")

        all_features.extend(features)

        params = None

        next_url = None

        for link in data.get("links", []):
            if link.get("rel") == "next":
                next_url = link.get("href")
                break

        if next_url is None:
            print("done")
            break

        url = next_url

        page_number += 1

        time.sleep(0.2)

    print(f"total downloards: {len(all_features)}")

    return {"features": all_features}

def process_data(data):

    rows = []

    for feature in data.get("features", []):

        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        coordinates = geometry.get("coordinates", [])

        if len(coordinates) < 2:
            continue

        value = properties.get("value")

        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        rows.append({
            "station_id": properties.get(
                "monitoring_location_id"
            ),

            "station_name": properties.get(
                "monitoring_location_name"
            ),

            "time": properties.get("time"),

            "parameter_code": properties.get(
                "parameter_code"
            ),

            "value": value,

            "unit": properties.get(
                "unit_of_measure"
            ),

            "lat": coordinates[1],

            "lng": coordinates[0],
        })

    df = pandas.DataFrame(rows)

    return df

def clean_data(df):

    if df.empty:
        return df

    # Convert time to pandas datetime
    df["time"] = pandas.to_datetime(
        df["time"],
        errors="coerce"
    )

    # Remove rows with invalid timestamps
    df = df.dropna(subset=["time"])

    # Remove rows without station IDs
    df = df.dropna(subset=["station_id"])

    # Sort chronologically
    df = df.sort_values(
        ["station_id", "time"]
    )

    # Remove exact duplicate observations
    df = df.drop_duplicates(
        subset=[
            "station_id",
            "time",
            "parameter_code"
        ]
    )

    # Reset index
    df = df.reset_index(drop=True)

    return df

def main():

    data = download_data()

    print(
        f"\nRaw feature count: "
        f"{len(data.get('features', []))}"
    )

    df = process_data(data)

    print(
        f"Processed records: {len(df)}"
    )

 
    df = clean_data(df)

    print(
        f"Records after cleaning: {len(df)}"
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"\nSaved dataset to:\n{OUTPUT_FILE}")

 
    print("\nFirst 10 rows:")
    print(df.head(10).to_string(index=False))


    if not df.empty:

        print("\nDataset information:")

        print(
            f"Number of stations: "
            f"{df['station_id'].nunique()}"
        )

        print(
            f"Date range: "
            f"{df['time'].min()} -> "
            f"{df['time'].max()}"
        )

        print(
            f"Number of measurements: "
            f"{len(df)}"
        )


if __name__ == "__main__":
    main()
