# Production Keycloak: built once with our settings, so it starts faster and uses less memory.
# Build from the repo root:
#   docker build --build-context styles=apps/web/src/styles -f infra/keycloak/Dockerfile infra/keycloak
FROM quay.io/keycloak/keycloak:26.8.1 AS build
ENV KC_DB=postgres \
    KC_HEALTH_ENABLED=true \
    KC_HTTP_RELATIVE_PATH=/auth
COPY themes/costpilot /opt/keycloak/themes/costpilot
# The login page uses the same colours as the app, from the one token file.
COPY --from=styles tokens.css /opt/keycloak/themes/costpilot/login/resources/css/shared/tokens.css
# Keycloak 26.8.1 ships Guava 33.6.0, which has a known denial-of-service bug (CVE-2026-102554).
# Swap in the fixed 33.7.2 until Keycloak ships it (keycloak/keycloak#54110). The file keeps its
# old name, because Keycloak's build step lists its libraries by file name.
ADD --chown=1000:0 --checksum=sha256:b530942257fb935f8b2cfaa5f8eb5bd59c555fd8e8d01b8ce98912e077ea606c \
  https://repo1.maven.org/maven2/com/google/guava/guava/33.7.2-jre/guava-33.7.2-jre.jar \
  /opt/keycloak/lib/lib/main/com.google.guava.guava-33.6.0-jre.jar
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.8.1
COPY --from=build /opt/keycloak/ /opt/keycloak/
COPY realm-costpilot.json /opt/keycloak/data/import/realm-costpilot.json
USER 1000
# Healthy only once the CostPilot realm answers. Keycloak's own "ready" comes before the realm is loaded.
# The image has no curl, so the check talks HTTP with bash.
HEALTHCHECK --interval=10s --timeout=5s --retries=30 --start-period=60s \
  CMD ["bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/8080 && printf 'GET /auth/realms/%s/.well-known/openid-configuration HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' \"$KEYCLOAK_REALM\" >&3 && head -n 1 <&3 | grep -q ' 200'"]
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
