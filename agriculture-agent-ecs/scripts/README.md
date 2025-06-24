# Scripts Directory

Simple scripts for managing the Agriculture Agent Docker services.

## Scripts

### start_docker.sh
Starts all Docker services with AWS credentials (if available).
```bash
./scripts/start_docker.sh
```

### stop_docker.sh
Stops all Docker services.  
```bash
./scripts/stop_docker.sh
```

### test_docker.sh
Tests the running services by checking endpoints and running sample queries.
```bash
./scripts/test_docker.sh
```

## Typical Workflow

1. Start services: `./scripts/start_docker.sh`
2. Test services: `./scripts/test_docker.sh`
3. Stop services: `./scripts/stop_docker.sh`

## Notes

- The start script will automatically export AWS credentials if AWS CLI is configured
- The test script only tests endpoints; it doesn't start or stop services
- All scripts should be run from the project root or scripts directory