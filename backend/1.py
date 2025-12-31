import numpy as np
from model_server import ModelServer

s = ModelServer()

for p in ["uniswap_v2_usdc_eth", "uniswap_v2_dai_eth", "aave_v3_eth"]:
    X = np.array([[s.get_latest_snapshot(p)[f] for f in s.feature_names]])
    print(p, X)
