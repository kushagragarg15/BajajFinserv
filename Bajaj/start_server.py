#!/usr/bin/env python3
"""
Server Startup Script

This script starts the optimized server with proper error handling and environment setup.
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables and dependencies are available"""
    logger.info("🔍 Checking environment...")
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        logger.error("❌ main.py not found. Please run this script from the Bajaj directory.")
        return False
    
    # Check if app directory exists
    if not Path("app").exists():
        logger.error("❌ app directory not found. Please ensure the optimized code is in place.")
        return False
    
    # Check critical dependencies
    try:
        import fastapi
        import uvicorn
        import aiohttp
        import langchain
        logger.info("✅ Core dependencies available")
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False
    
    # Check environment variables (optional - will use defaults if not set)
    env_vars = [
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT", 
        "GOOGLE_API_KEY"
    ]
    
    missing_env_vars = []
    for var in env_vars:
        if not os.getenv(var):
            missing_env_vars.append(var)
    
    if missing_env_vars:
        logger.warning(f"⚠️ Missing environment variables: {missing_env_vars}")
        logger.warning("The server may not work properly without these. Check your .env file.")
    else:
        logger.info("✅ Environment variables configured")
    
    return True

def start_server():
    """Start the optimized server"""
    logger.info("🚀 Starting optimized server...")
    
    try:
        import uvicorn
        from main import app
        
        logger.info("Server will be available at: http://localhost:8000")
        logger.info("Health check: http://localhost:8000/health")
        logger.info("API endpoint: http://localhost:8000/api/v1/hackrx/run")
        logger.info("Performance stats: http://localhost:8000/performance")
        logger.info("Performance analysis: http://localhost:8000/performance/analysis")
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")
        logger.info("=" * 60)
        
        # Start the server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        logger.error("Check the error details above and ensure all dependencies are installed.")
        return False
    
    return True

def main():
    """Main function"""
    print("🔧 Optimized Server Startup")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n✅ Environment check passed!")
    print("Starting server...")
    
    # Start server
    success = start_server()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()