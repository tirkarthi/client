import warnings

import numpy
from sacred.dependencies import get_digest
from sacred.observers import RunObserver

import wandb


class WandbObserver(RunObserver):
    """Log sacred experiment data to W&B.

    Arguments:
        Accepts all the arguments accepted by wandb.init().

        name — A display name for this run, which shows up in the UI and is editable, doesn't have to be unique
        notes — A multiline string description associated with the run
        config — a dictionary-like object to set as initial config
        project — the name of the project to which this run will belong
        tags — a list of strings to associate with this run as tags
        dir — the path to a directory where artifacts will be written (default: ./wandb)
        entity — the team posting this run (default: your username or your default team)
        job_type — the type of job you are logging, e.g. eval, worker, ps (default: training)
        save_code — save the main python or notebook file to wandb to enable diffing (default: editable from your settings page)
        group — a string by which to group other runs; see Grouping
        reinit — whether to allow multiple calls to wandb.init in the same process (default: False)
        id — A unique ID for this run primarily used for Resuming. It must be globally unique, and if you delete a run you can't reuse the ID. Use the name field for a descriptive, useful name for the run. The ID cannot contain special characters.
        resume — if set to True, the run auto resumes; can also be a unique string for manual resuming; see Resuming (default: False)
        anonymous — can be "allow", "never", or "must". This enables or explicitly disables anonymous logging. (default: never)
        force — whether to force a user to be logged into wandb when running a script (default: False)
        magic — (bool, dict, or str, optional): magic configuration as bool, dict, json string, yaml filename. If set to True will attempt to auto-instrument your script. (default: None)
        sync_tensorboard — A boolean indicating whether or not copy all TensorBoard logs wandb; see Tensorboard (default: False)
        monitor_gym — A boolean indicating whether or not to log videos generated by OpenAI Gym; see Ray Tune (default: False)
        allow_val_change — whether to allow wandb.config values to change, by default we throw an exception if config values are overwritten. (default: False)

    Examples:
        Create sacred experiment::
        from wandb.sacred import WandbObserver
        ex.observers.append(WandbObserver(project='sacred_test',
                                                name='test1'))
        @ex.config
        def cfg():
            C = 1.0
            gamma = 0.7
        @ex.automain
        def run(C, gamma, _run):
            iris = datasets.load_iris()
            per = permutation(iris.target.size)
            iris.data = iris.data[per]
            iris.target = iris.target[per]
            clf = svm.SVC(C, 'rbf', gamma=gamma)
            clf.fit(iris.data[:90],
                    iris.target[:90])
            return clf.score(iris.data[90:],
                                iris.target[90:])
    """

    def __init__(self, **kwargs):
        self.run = wandb.init(**kwargs)
        self.resources = {}

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        # TODO: add the source code file
        # TODO: add dependencies and metadata.
        self.__update_config(config)

    def completed_event(self, stop_time, result):
        if result:
            if not isinstance(result, tuple):
                result = (
                    result,
                )  # transform single result to tuple so that both single & multiple results use same code

            for i, r in enumerate(result):
                if isinstance(r, float) or isinstance(r, int):
                    wandb.log({f"result_{i}": float(r)})
                elif isinstance(r, dict):
                    wandb.log(r)
                elif isinstance(r, object):
                    artifact = wandb.Artifact(f"result_{i}.pkl", type="result")
                    artifact.add_file(r)
                    self.run.log_artifact(artifact)
                elif isinstance(r, numpy.ndarray):
                    wandb.log({f"result_{i}": wandb.Image(r)})
                else:
                    warnings.warn(
                        f"logging results does not support type '{type(r)}' results. Ignoring this result",
                        stacklevel=2,
                    )

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        if content_type is None:
            content_type = "file"
        artifact = wandb.Artifact(name, type=content_type)
        artifact.add_file(filename)
        self.run.log_artifact(artifact)

    def resource_event(self, filename):
        """TODO: Maintain resources list."""
        if filename not in self.resources:
            md5 = get_digest(filename)
            self.resources[filename] = md5

    def log_metrics(self, metrics_by_name, info):
        for metric_name, metric_ptr in metrics_by_name.items():
            for _step, value in zip(metric_ptr["steps"], metric_ptr["values"]):
                if isinstance(value, numpy.ndarray):
                    wandb.log({metric_name: wandb.Image(value)})
                else:
                    wandb.log({metric_name: value})

    def __update_config(self, config):
        for k, v in config.items():
            self.run.config[k] = v
        self.run.config["resources"] = []
