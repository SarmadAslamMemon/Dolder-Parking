FROM nginx:1.19.7-alpine

# Add required tools
# - bash: to run our start script
# - gettext: for envsubst
# - curl: for healthcheck
RUN apk add --no-cache bash gettext curl

# Add nginx.conf to container
COPY --chown=nginx:nginx nginx.conf /etc/nginx/nginx.conf
COPY --chown=nginx:nginx start.sh /app/start.sh
# Normalize Windows line endings to Unix to avoid exec format errors
RUN sed -i 's/\r$//' /app/start.sh

# set workdir
WORKDIR /app

# permissions and nginx user for tightened security
RUN chown -R nginx:nginx /app && chmod -R 755 /app && \
        chown -R nginx:nginx /var/cache/nginx && \
        chown -R nginx:nginx /var/log/nginx && \
        chmod -R 755 /var/log/nginx && \
        chown -R nginx:nginx /etc/nginx/conf.d
RUN touch /var/run/nginx.pid && chown -R nginx:nginx /var/run/nginx.pid
RUN chmod +x /app/start.sh

# # Uncomment to keep the nginx logs inside the container - Leave commented for logging to stdout and stderr
# RUN mkdir -p /var/log/nginx
# RUN unlink /var/log/nginx/access.log \
#     && unlink /var/log/nginx/error.log \
#     && touch /var/log/nginx/access.log \
#     && touch /var/log/nginx/error.log \
#     && chown nginx /var/log/nginx/*log \
#     && chmod 644 /var/log/nginx/*log

# Run as root so nginx can bind to port 80; it will drop privileges internally
# (The official nginx entrypoint starts master process as root, workers as nginx)
USER root

CMD ["nginx", "-g", "daemon off;"]