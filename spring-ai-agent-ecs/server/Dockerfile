# Simple development Dockerfile
FROM maven:3.9.6-eclipse-temurin-21

WORKDIR /app

# Copy parent pom.xml
COPY pom.xml ./pom.xml

# Copy server module
COPY server ./server

# Change to server directory
WORKDIR /app/server

# Download dependencies
RUN mvn dependency:go-offline -B

# Build the application
RUN mvn clean package -DskipTests -B

# Expose port
EXPOSE 8010

# Run the application
CMD ["java", "-jar", "target/server-1.0.0-SNAPSHOT.jar"]