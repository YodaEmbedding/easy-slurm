import yaml

import easy_slurm


def main():
    with open("job.yaml") as f:
        job_config = yaml.safe_load(f)

    easy_slurm.submit_job(**job_config)


if __name__ == "__main__":
    main()
