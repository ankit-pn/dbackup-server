docker-compose down &&
docker rmi -f dbackup-server_fastapi-server dbackup-server_scheduler &&
git pull &&
docker-compose up &&
echo "All commands executed successfully!"