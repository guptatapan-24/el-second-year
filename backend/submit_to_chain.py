#!/usr/bin/env python3
"""Submit signed risk payloads to blockchain"""

import json
import time
from typing import Dict
from web3 import Web3
from eth_account import Account
from config import config
from database import SessionLocal, RiskSubmission
from datetime import datetime

# Oracle contract ABI (minimal for submitRisk function)
ORACLE_ABI = json.loads('''[
    {
        "inputs": [
            {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
            {"internalType": "uint16", "name": "score", "type": "uint16"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
            {"internalType": "bytes32", "name": "cidHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "nonce", "type": "uint256"}
        ],
        "name": "submitRisk",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "internalType": "bytes32", "name": "poolId", "type": "bytes32"},
            {"indexed": false, "internalType": "uint16", "name": "score", "type": "uint16"},
            {"indexed": false, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": false, "internalType": "bytes32", "name": "cidHash", "type": "bytes32"}
        ],
        "name": "RiskUpdated",
        "type": "event"
    }
]''')

class ChainSubmitter:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.ETH_RPC_URL))
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Ethereum RPC: {config.ETH_RPC_URL}")
        
        print(f"Connected to Ethereum network (chain ID: {self.w3.eth.chain_id})")
        
        # Setup account
        self.account = Account.from_key(config.SIGNER_PRIVATE_KEY)
        self.address = self.account.address
        print(f"Submitter address: {self.address}")
        
        # Check balance
        balance = self.w3.eth.get_balance(self.address)
        print(f"Account balance: {self.w3.from_wei(balance, 'ether')} ETH")
    
    def get_oracle_contract(self):
        """Get oracle contract instance"""
        if not config.ORACLE_CONTRACT_ADDRESS or \
           config.ORACLE_CONTRACT_ADDRESS == '0x' + '0'*40:
            raise ValueError("ORACLE_CONTRACT_ADDRESS not set. Deploy contract first.")
        
        return self.w3.eth.contract(
            address=config.ORACLE_CONTRACT_ADDRESS,
            abi=ORACLE_ABI
        )
    
    def prepare_contract_params(self, payload: Dict) -> Dict:
        """Convert payload to contract function parameters"""
        # Convert pool_id to bytes32
        pool_id_str = payload['pool_id']
        if pool_id_str.startswith('0x'):
            pool_id_bytes32 = self.w3.to_bytes(hexstr=pool_id_str.ljust(66, '0'))
        else:
            pool_id_bytes32 = self.w3.keccak(text=pool_id_str)
        
        # Convert CID to bytes32 hash
        cid = payload.get('artifact_cid', 'QmDefault')
        cid_hash = self.w3.keccak(text=cid)
        
        # Convert signature to bytes
        signature = bytes.fromhex(payload['signature'].replace('0x', ''))
        
        return {
            'poolId': pool_id_bytes32,
            'score': int(payload['risk_score']),
            'timestamp': payload['timestamp'],
            'signature': signature,
            'cidHash': cid_hash,
            'nonce': payload['nonce']
        }
    
    def submit_risk(self, signed_payload: Dict) -> str:
        """Submit signed risk to blockchain"""
        try:
            contract = self.get_oracle_contract()
            params = self.prepare_contract_params(signed_payload)
            
            # Build transaction
            tx = contract.functions.submitRisk(
                params['poolId'],
                params['score'],
                params['timestamp'],
                params['signature'],
                params['cidHash'],
                params['nonce']
            ).build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            # Sign transaction
            signed_tx = self.account.sign_transaction(tx)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            print(f"Transaction sent: {tx_hash_hex}")
            
            # Store in database
            self._store_submission(signed_payload, tx_hash_hex, 'pending')
            
            # Wait for confirmation (with timeout)
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    print(f"Transaction confirmed in block {receipt['blockNumber']}")
                    self._update_submission_status(tx_hash_hex, 'confirmed')
                    return tx_hash_hex
                else:
                    print(f"Transaction failed")
                    self._update_submission_status(tx_hash_hex, 'failed')
                    raise Exception("Transaction failed")
            
            except Exception as e:
                print(f"Timeout waiting for confirmation: {e}")
                return tx_hash_hex
                
        except Exception as e:
            print(f"Error submitting to chain: {e}")
            raise
    
    def _store_submission(self, payload: Dict, tx_hash: str, status: str):
        """Store submission in database"""
        db = SessionLocal()
        try:
            submission = RiskSubmission(
                pool_id=payload['pool_id'],
                risk_score=payload['risk_score'],
                timestamp=datetime.utcnow(),
                top_reasons=payload.get('top_reasons', []),
                model_version=payload.get('model_version', ''),
                artifact_cid=payload.get('artifact_cid', ''),
                signature=payload.get('signature', ''),
                tx_hash=tx_hash,
                nonce=payload.get('nonce', 0),
                status=status
            )
            db.add(submission)
            db.commit()
        finally:
            db.close()
    
    def _update_submission_status(self, tx_hash: str, status: str):
        """Update submission status"""
        db = SessionLocal()
        try:
            submission = db.query(RiskSubmission).filter(
                RiskSubmission.tx_hash == tx_hash
            ).first()
            if submission:
                submission.status = status
                db.commit()
        finally:
            db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Submit risk to blockchain')
    parser.add_argument('--payload', required=True, help='Path to signed payload JSON')
    args = parser.parse_args()
    
    try:
        # Load payload
        with open(args.payload, 'r') as f:
            payload = json.load(f)
        
        print("\n=== Submitting Risk to Chain ===")
        print(f"Pool: {payload['pool_id']}")
        print(f"Risk Score: {payload['risk_score']}")
        
        submitter = ChainSubmitter()
        tx_hash = submitter.submit_risk(payload)
        
        print(f"\n✓ Success! Transaction: {tx_hash}")
        print(f"View on explorer: https://sepolia.etherscan.io/tx/{tx_hash}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
