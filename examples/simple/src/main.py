from argparse import ArgumentParser
from time import sleep

import tomlkit as toml


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--resume", dest="resume", action="store_true")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    with open("../assets/config.toml") as f:
        config = toml.loads(f.read())

    if args.resume:
        with open("../results/state_dict.toml") as f:
            state_dict = toml.loads(f.read())
    else:
        state_dict = {"epoch": 0}

    max_epochs = config["epochs"]
    start_epoch = state_dict["epoch"]
    end_epoch = min(max_epochs, start_epoch + 10)

    for epoch in range(start_epoch, end_epoch):
        print(f"Epoch: {epoch}", flush=True)
        state_dict["epoch"] = epoch + 1

        with open("../results/state_dict.toml", "w") as f:
            f.write(toml.dumps(state_dict))

        sleep(5)


if __name__ == "__main__":
    main()
