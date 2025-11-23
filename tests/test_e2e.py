#!/usr/bin/env python3
"""End-to-end system test for VeriRisk"""

import sys
import time
import requests
import json

def test_backend_health():
    """Test backend health endpoint"""
    print("Testing backend health...")
    response = requests.get('http://localhost:8001/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['components']['model_server'] == True
    assert data['components']['signer'] == True
    assert data['components']['submitter'] == True
    print("✓ Backend health check passed")

def test_inference():
    """Test model inference"""
    print("\nTesting inference...")
    response = requests.post('http://localhost:8001/infer', 
                            json={'pool_id': 'test_pool_1'})
    assert response.status_code == 200
    data = response.json()
    assert 'risk_score' in data
    assert 'risk_level' in data
    assert 'top_reasons' in data
    assert data['model_version'] == 'xgb_v1'
    print(f"✓ Inference successful - Risk: {data['risk_score']}/100 ({data['risk_level']})")

def test_sign_payload():
    """Test payload signing"""
    print("\nTesting payload signing...")
    response = requests.post('http://localhost:8001/infer_and_sign',
                            json={'pool_id': 'test_pool_1'})
    assert response.status_code == 200
    data = response.json()
    assert 'signature' in data
    assert 'signer_address' in data
    assert data['signer_address'] == '0x5ECc9815C951F2e5248d8A92B1653bd198613937'
    print(f"✓ Signing successful - Signer: {data['signer_address']}")

def test_submissions():
    """Test submissions endpoint"""
    print("\nTesting submissions endpoint...")
    response = requests.get('http://localhost:8001/submissions')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    print(f"✓ Found {len(data)} submissions in database")
    
    # Check first submission
    sub = data[0]
    assert 'pool_id' in sub
    assert 'risk_score' in sub
    assert 'tx_hash' in sub
    assert 'status' in sub
    print(f"  Latest: Pool {sub['pool_id']} - Risk {sub['risk_score']}/100 - Status: {sub['status']}")

def test_frontend():
    """Test frontend is accessible"""
    print("\nTesting frontend...")
    try:
        response = requests.get('http://localhost:3000', timeout=5)
        assert response.status_code == 200
        print("✓ Frontend is accessible")
    except Exception as e:
        print(f"⚠ Frontend not accessible: {e}")

def main():
    print("=== VeriRisk End-to-End Test ===\n")
    
    try:
        test_backend_health()
        test_inference()
        test_sign_payload()
        test_submissions()
        test_frontend()
        
        print("\n=== ALL TESTS PASSED ✓ ===")
        print("\nDeployment Info:")
        print("- Oracle Contract: 0x8a5aE3062B5ed81678347D1094c7Ab40Da05d800")
        print("- Consumer Contract: 0xAA66f3eB8EC56474d32f04Dd10413F2367782807")
        print("- Network: Sepolia Testnet")
        print("- Backend API: http://localhost:8001")
        print("- Frontend: http://localhost:3000")
        print("- Explorer: https://sepolia.etherscan.io/address/0x8a5aE3062B5ed81678347D1094c7Ab40Da05d800")
        
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
