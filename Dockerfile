FROM frappe/bench:latest

ARG FRAPPE_VERSION=version-15
ARG ERPNEXT_VERSION=version-15

USER frappe
WORKDIR /home/frappe

# Initialize bench with Frappe
RUN bench init frappe-bench \
    --frappe-branch ${FRAPPE_VERSION} \
    --skip-redis-config-generation \
    --verbose

WORKDIR /home/frappe/frappe-bench

# Get ERPNext
RUN bench get-app erpnext --branch ${ERPNEXT_VERSION}

# Configure bench for development
RUN bench set-config -g db_host mariadb && \
    bench set-config -g redis_cache redis://redis-cache:6379 && \
    bench set-config -g redis_queue redis://redis-queue:6379 && \
    bench set-config -g developer_mode 1 && \
    bench set-config -g serve_default_site 1

# Install Node dependencies
RUN bench setup requirements --dev

# The custom app (erpnext_mexico) is mounted as a volume at runtime
# This makes live development possible without rebuilding

EXPOSE 8080 9000 6787

CMD ["bench", "start"]
