from argparse import ArgumentParser

from datasets import load_dataset, concatenate_datasets


def get_args():
    parser = ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True, help="Dataset name")
    parser.add_argument('--datasets-to-concatenate', type=lambda s: s.split(','), required=True, help="List of datasets to concatenate in order to obtain final dataset")

    args = parser.parse_args()

    assert args.dataset not in args.datasets_to_concatenate

    return args

def compute_external_ids_(ds):
    """This is done at the end of processing and we basically convert `external_urls` in `external_ids`"""
    # For each url, find the most recent row id corresponding to that url
    # All of the duplicate of a `url` are either all in that dictionary or not in that dictionary
    # This table allows me to do a double join so I can easily compute the ids.
    # We'll then go through that csv and add the ids to final dataset.
    # No duplicates guaranteed
    url_to_id_and_timestamp = {}
    # TODO: batch this
    for data in ds:
        url = data["url"]
        id_ = data["id"]
        timestamp = data["fetch_time"]
        if url in url_to_id_and_timestamp:
            old_id, old_time_stamp = url_to_id_and_timestamp[url]
            new_timestamp, new_id = max((timestamp, id_), (old_time_stamp, old_id))
            url_to_id_and_timestamp[url] = (new_id, new_timestamp)
        else:
            url_to_id_and_timestamp[url] = (id_, timestamp)

    # TODO: batch this
    for data in ds:
        # Not all urls are part of our index. We keep `external_urls` for this sake.
        data["external_ids"] = [
            url_to_id_and_timestamp[external_url][0]
            for external_url in data["external_urls"]
            if external_url in url_to_id_and_timestamp
        ]

    return ds

def assign_id(batch, indices):
    batch["id"] = indices
    return batch

def main():
    args = get_args()

    datasets = [
        load_dataset(dataset_name, use_auth_token=True, split="train")
        for dataset_name in args.datasets_to_concatenate
    ]

    # Concatenate all the splits together
    ds = concatenate_datasets(datasets)

    # Generate id
    ds = ds.map(assign_id, batched=True, with_indices=True)

    # Generate external_ids
    ds = compute_external_ids_(ds)

    # Add as train split
    ds.push_to_hub(args.dataset, private=True)

if __name__ == "__main__":
    main()