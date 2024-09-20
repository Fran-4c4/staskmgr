# Simple Task Manager (STMGR)

## Key Differences from Celery

### Task Registration
Celery is based on a broker (like Redis/RabbitMQ) for task queuing and scheduling, requiring you to register tasks with hardcoded definitions. In contrast, STMGR doesn't rely on hardcoded classes; the handlers are dynamically loaded, allowing for changes to modules at any time, as long as they are in an accessible path.

### Broker
- **STMGR**: Relies on a database (Postgres in this case). This design can be extended, but I’ve chosen this for my specific needs.
- **Celery**: Relies heavily on a broker like Redis or RabbitMQ.

### Flexibility
- **STMGR**: More flexible, allowing for configuration changes through a database without deploying new code.
- **Celery**: Task definitions must be present in the codebase (modifying them requires redeployment).

### Distribution
- **STMGR**: Designed with distribution in mind; example tasks can be executed in AWS ECS or Docker. You can create any handler you need with custom configurations stored in a database.
- **Celery**: Focused on task execution using brokers.

### Multiple STMGR Instances
- You can create multiple STMGR instances by configuring them in the database with a key-name. When starting the task manager, specify the key.