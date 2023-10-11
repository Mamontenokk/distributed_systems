# Replicated log
Implementation of replicated log for distributed systems course

## How to build
```bash
docker build -t replicated_log_secondary -f Dockerfile.secondary .
docker build -t replicated_log_main -f Dockerfile.main .
```

## How to run
```bash 
docker compose up
```