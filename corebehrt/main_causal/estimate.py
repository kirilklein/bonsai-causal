import logging

from corebehrt.functional.setup.args import get_args
from corebehrt.modules.causal.estimate import EffectEstimator
from corebehrt.modules.setup.config import load_config
from corebehrt.modules.setup.causal.directory import CausalDirectoryPreparer

CONFIG_PATH = "./corebehrt/configs/causal/estimate/estimate.yaml"


def main_estimate(config_path):
    cfg = load_config(config_path)

    # Setup directories
    CausalDirectoryPreparer(cfg).setup_estimate()

    # Logger
    logger = logging.getLogger("estimate")
    logger.info("Loaded estimate config from: %s", config_path)
    print(f"[estimate] Loaded config from: {config_path}", flush=True)
    try:
        estimator_section = dict(cfg.estimator)
    except Exception:
        estimator_section = cfg.get("estimator", {})
    logger.info("Raw estimator config section: %s", estimator_section)
    print(f"[estimate] Raw estimator config: {estimator_section}", flush=True)

    estimator = EffectEstimator(cfg, logger)
    estimator.run()
    # Load data
    logger.info("Done")


if __name__ == "__main__":
    args = get_args(CONFIG_PATH)
    main_estimate(args.config_path)
