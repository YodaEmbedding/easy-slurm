from argparse import ArgumentParser
from time import sleep

import yaml


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--resume", dest="resume", action="store_true")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    with open("../assets/hparams.yaml") as f:
        hparams = yaml.safe_load(f)

    if args.resume:
        with open("../results/state_dict.yaml") as f:
            state_dict = yaml.safe_load(f)
    else:
        state_dict = {"epoch": 0}

    max_epochs = hparams["hp"]["epochs"]
    start_epoch = state_dict["epoch"]
    end_epoch = min(max_epochs, start_epoch + 10)

    for epoch in range(start_epoch, end_epoch):
        print(f"Epoch: {epoch}", flush=True)
        state_dict["epoch"] = epoch + 1

        with open("../results/state_dict.yaml", "w") as f:
            yaml.safe_dump(state_dict, f)

        sleep(5)


if __name__ == "__main__":
    main()
