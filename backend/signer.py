#!/usr/bin/env python3
"""Cryptographic signing module for risk payloads"""

import json
import hashlib
from typing import Dict
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from config import config

class PayloadSigner:
    def __init__(self, private_key: str = None):
        self.private_key = private_key or config.SIGNER_PRIVATE_KEY
        if not self.private_key or self.private_key == '0x' + '0'*64:
            raise ValueError("Invalid private key. Set SIGNER_PRIVATE_KEY in .env")
        
        # Derive account from private key
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        print(f"Signer address: {self.address}")
    
    def canonical_json(self, obj: Dict) -> str:
        """Create canonical JSON representation (sorted keys, no whitespace)"""
        return json.dumps(obj, sort_keys=True, separators=(',', ':'))
    
    def create_payload(self, pool_id: str, risk_score: float, 
                      top_reasons: list, model_version: str,
                      artifact_cid: str = "Qm...", nonce: int = None) -> Dict:
        """Create canonical risk payload"""
        import time
        
        if nonce is None:
            nonce = int(time.time())
        
        payload = {
            'pool_id': pool_id,
            'risk_score': round(risk_score, 2),
            'top_reasons': top_reasons,
            'model_version': model_version,
            'artifact_cid': artifact_cid,
            'timestamp': int(time.time()),
            'nonce': nonce
        }
        
        return payload
    
    def sign_payload(self, payload: Dict) -> Dict:
        """Sign payload using Solidity-compatible encoding"""
        from web3 import Web3
        
        # Convert pool_id to bytes32
        pool_id_str = payload['pool_id']
        if pool_id_str.startswith('0x') and len(pool_id_str) == 66:
            pool_id_bytes32 = bytes.fromhex(pool_id_str[2:])
        else:
            pool_id_bytes32 = Web3.keccak(text=pool_id_str)
        
        # Convert CID to bytes32 hash
        cid = payload.get('artifact_cid', 'QmDefault')
        cid_hash = Web3.keccak(text=cid)
        
        # Prepare parameters matching Solidity: (poolId, score, timestamp, cidHash, nonce)
        score = int(payload['risk_score'])
        timestamp = payload['timestamp']
        nonce = payload['nonce']
        
        # Create hash matching Solidity: keccak256(abi.encodePacked(...))
        # Note: abi.encodePacked doesn't pad values
        packed_data = (
            pool_id_bytes32 +
            score.to_bytes(2, 'big') +  # uint16
            timestamp.to_bytes(32, 'big') +  # uint256
            cid_hash +  # bytes32
            nonce.to_bytes(32, 'big')  # uint256
        )
        
        message_hash = Web3.keccak(packed_data)
        
        # Create Ethereum signed message
        message = encode_defunct(primitive=message_hash)
        
        # Sign
        signed_message = self.account.sign_message(message)
        
        # Return payload with signature
        signed_payload = payload.copy()
        signed_payload['signature'] = signed_message.signature.hex()
        signed_payload['signer_address'] = self.address
        signed_payload['_pool_id_bytes32'] = pool_id_bytes32.hex()
        signed_payload['_cid_hash'] = cid_hash.hex()
        
        return signed_payload
    
    def verify_signature(self, payload: Dict, signature: str) -> bool:
        """Verify signature (for testing)"""
        # Remove signature from payload
        payload_copy = payload.copy()
        payload_copy.pop('signature', None)
        payload_copy.pop('signer_address', None)
        
        # Create canonical JSON and hash
        canonical = self.canonical_json(payload_copy)
        message_hash = hashlib.sha256(canonical.encode()).digest()
        message = encode_defunct(primitive=message_hash)
        
        # Recover address from signature
        try:
            recovered_address = Account.recover_message(message, signature=signature)
            return recovered_address.lower() == self.address.lower()
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def generate_test_keypair():
        """Generate a new ephemeral test keypair"""
        account = Account.create()
        return {
            'private_key': account.key.hex(),
            'address': account.address
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sign risk payloads')
    parser.add_argument('--generate-key', action='store_true',
                       help='Generate new test keypair')
    parser.add_argument('--test-sign', action='store_true',
                       help='Test signing workflow')
    args = parser.parse_args()
    
    if args.generate_key:
        keypair = PayloadSigner.generate_test_keypair()
        print("\n=== New Test Keypair ===")
        print(f"Private Key: {keypair['private_key']}")
        print(f"Address: {keypair['address']}")
        print("\nAdd to .env file:")
        print(f"SIGNER_PRIVATE_KEY={keypair['private_key']}")
    
    elif args.test_sign:
        try:
            signer = PayloadSigner()
            
            # Test payload
            payload = signer.create_payload(
                pool_id='0xtest123',
                risk_score=75.5,
                top_reasons=[
                    {'feature': 'tvl_pct_change_1h', 'impact': -15.2},
                    {'feature': 'reserve_imbalance', 'impact': 0.35},
                ],
                model_version='xgb_v1'
            )
            
            print("\n=== Unsigned Payload ===")
            print(json.dumps(payload, indent=2))
            
            # Sign
            signed = signer.sign_payload(payload)
            
            print("\n=== Signed Payload ===")
            print(json.dumps(signed, indent=2))
            
            # Verify
            is_valid = signer.verify_signature(signed, signed['signature'])
            print(f"\nSignature valid: {is_valid}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("Use --generate-key or --test-sign")
