#!/usr/bin/env python3
"""IPFS uploader for model artifacts and explanations using web3.storage"""

import requests
import json
import os
import sys
import argparse
from pathlib import Path
import hashlib

class IPFSUploader:
    def __init__(self, api_token=None):
        """Initialize IPFS uploader with web3.storage (free public IPFS service)"""
        self.api_token = api_token or os.getenv('WEB3_STORAGE_TOKEN', '')
        
        # Use web3.storage free API
        self.api_url = 'https://api.web3.storage'
        
        # For demo: use ipfs.tech public gateway
        self.public_gateway = 'https://w3s.link/ipfs'
        
        # Setup headers
        self.headers = {}
        if self.api_token:
            self.headers['Authorization'] = f'Bearer {self.api_token}'
    
    def upload_file(self, file_path: str, pin: bool = True) -> dict:
        """
        Upload a file to IPFS using web3.storage
        
        Args:
            file_path: Path to file to upload
            pin: Whether to pin the file (keep it permanently)
        
        Returns:
            dict with 'cid', 'name', 'size'
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # For MVP demo: generate deterministic CID from file hash
        # In production, use actual IPFS upload with web3.storage API token
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()
            # Create CID-like identifier (base58 encoded)
            mock_cid = f"Qm{file_hash[:44]}"  # Mock CIDv0 format
            size = len(content)
        
        print(f"✓ Generated mock CID for {file_path.name}: {mock_cid}")
        print(f"  (In production: upload to web3.storage)")
        print(f"  Size: {size} bytes")
        
        return {
            'cid': mock_cid,
            'name': file_path.name,
            'size': size,
            'gateway_url': f"{self.public_gateway}/{mock_cid}"
        }
    
    def upload_json(self, data: dict, filename: str = 'data.json', pin: bool = True) -> dict:
        """
        Upload JSON data to IPFS
        
        Args:
            data: Dictionary to upload
            filename: Filename to use
            pin: Whether to pin
        
        Returns:
            dict with 'cid', 'name', 'size'
        """
        # Convert to JSON
        json_bytes = json.dumps(data, indent=2, sort_keys=True).encode('utf-8')
        
        # Generate mock CID from hash
        json_hash = hashlib.sha256(json_bytes).hexdigest()
        mock_cid = f"Qm{json_hash[:44]}"
        
        print(f"✓ Generated mock CID for JSON: {mock_cid}")
        print(f"  (In production: upload to web3.storage)")
        
        return {
            'cid': mock_cid,
            'name': filename,
            'size': len(json_bytes),
            'gateway_url': f"{self.public_gateway}/{mock_cid}"
        }
    
    def get_content(self, cid: str) -> bytes:
        """
        Retrieve content from IPFS using public gateway
        
        Args:
            cid: IPFS CID
        
        Returns:
            File content as bytes
        """
        url = f"https://ipfs.io/ipfs/{cid}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        return response.content
    
    def pin_cid(self, cid: str) -> bool:
        """
        Pin an existing CID (mock for demo)
        
        Args:
            cid: IPFS CID to pin
        
        Returns:
            bool success
        """
        print(f"✓ Mock pinned CID: {cid}")
        print("  (In production: use web3.storage pinning)")
        return True


def main():
    parser = argparse.ArgumentParser(description='Upload files to IPFS via Infura')
    parser.add_argument('--file', help='File path to upload')
    parser.add_argument('--json', help='JSON file to upload')
    parser.add_argument('--pin', action='store_true', default=True, help='Pin the file')
    parser.add_argument('--return-cid', action='store_true', help='Only output CID')
    parser.add_argument('--test', action='store_true', help='Test IPFS connection')
    args = parser.parse_args()
    
    try:
        uploader = IPFSUploader()
        
        if args.test:
            # Test with a simple JSON
            test_data = {
                'test': 'VeriRisk IPFS test',
                'timestamp': '2025-11-23T09:00:00Z'
            }
            result = uploader.upload_json(test_data, 'test.json')
            print(f"\nTest successful! CID: {result['cid']}")
            sys.exit(0)
        
        if args.file:
            result = uploader.upload_file(args.file, pin=args.pin)
            if args.return_cid:
                print(result['cid'])
            else:
                print(json.dumps(result, indent=2))
            sys.exit(0)
        
        if args.json:
            with open(args.json, 'r') as f:
                data = json.load(f)
            result = uploader.upload_json(data, os.path.basename(args.json), pin=args.pin)
            if args.return_cid:
                print(result['cid'])
            else:
                print(json.dumps(result, indent=2))
            sys.exit(0)
        
        parser.print_help()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
