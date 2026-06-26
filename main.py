from app.io.dataset_loader import DatasetLoader


def main():

    dataset = DatasetLoader.load("datasets/sample_candidate.json")

    for candidate in dataset:

        print(candidate.candidate_id)
        print(candidate.profile["current_title"])
        print(candidate.profile["current_company"])
        print("-" * 40)


if __name__ == "__main__":
    main()