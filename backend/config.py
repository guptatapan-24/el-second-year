import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Ethereum
    INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID', '')
    ETH_RPC_URL = os.getenv('ETH_RPC_URL', f"https://sepolia.infura.io/v3/{INFURA_PROJECT_ID}")
    SIGNER_PRIVATE_KEY = os.getenv('SIGNER_PRIVATE_KEY', '')
    ORACLE_CONTRACT_ADDRESS = os.getenv('ORACLE_CONTRACT_ADDRESS', '')
    
    # APIs
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
    THEGRAPH_API_KEY = os.getenv('THEGRAPH_API_KEY', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./veririsk.db')
    
    # IPFS
    IPFS_GATEWAY = os.getenv('IPFS_GATEWAY', 'https://ipfs.io/ipfs/')
    IPFS_API = os.getenv('IPFS_API', '/ip4/127.0.0.1/tcp/5001')
    
    # Model
    MODEL_PATH = os.getenv('MODEL_PATH', '../models/xgb_veririsk_v1.pkl')
    
    # Scheduler
    UPDATE_INTERVAL_SECONDS = int(os.getenv('UPDATE_INTERVAL_SECONDS', '300'))  # 5 minutes
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        if not cls.INFURA_PROJECT_ID:
            errors.append('INFURA_PROJECT_ID not set')
        if not cls.SIGNER_PRIVATE_KEY or cls.SIGNER_PRIVATE_KEY == '0x' + '0'*64:
            errors.append('SIGNER_PRIVATE_KEY not set or using default')
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        return True

config = Config()
