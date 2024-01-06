import os

import wandb

os.environ["WANDB_DOCKER"] = "my-test-container:dummy"

settings = wandb.Settings()
settings.update({"job_source": "image"})
run = wandb.init(
    project="test-job", config={"foo": "bar", "lr": 0.1, "epochs": 5}, settings=settings
)
for i in range(1, run.config["epochs"]):
    wandb.log({"loss": i})
run.finish()
