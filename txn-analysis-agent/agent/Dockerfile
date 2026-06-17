# AgentCore Runtime requires linux/arm64 (AWS Graviton) containers.
# Build with:  docker buildx build --platform linux/arm64 ...
# (the deploy.py script does this for you)

# ---- Stage 1: build the shaded (fat) jar ----
FROM --platform=linux/arm64 maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

# Cache dependencies first
COPY pom.xml .
RUN mvn -q -e -B dependency:go-offline

# Build the app
COPY src ./src
RUN mvn -q -e -B clean package -DskipTests

# ---- Stage 2: minimal runtime image ----
FROM --platform=linux/arm64 eclipse-temurin:17-jre
WORKDIR /app

# The shaded jar produced by maven-shade-plugin (Main-Class = RuntimeServer)
COPY --from=build /build/target/txn-analysis-agent-1.0-SNAPSHOT.jar /app/app.jar

# AgentCore Runtime HTTP contract listens on 8080
EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
