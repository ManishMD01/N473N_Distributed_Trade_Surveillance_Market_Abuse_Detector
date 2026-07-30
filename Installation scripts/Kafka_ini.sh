#!/bin/bash
#
#
java -version

sudo apt-get update

sudo apt-get install -y default-jdk

# Download Kafka

wget https://apache.org

wget https://archive.apache.org/dist/kafka/3.8.0/kafka_2.13-3.8.0.tgz

# Extract the files

tar -xzf kafka_2.13-3.9.0.tgz

rm kafka_2.13-3.9.0.tgz

# Move into the Kafka directory

cd kafka_2.13-3.9.0

KAFKA_CLUSTER_ID=$(bin/kafka-storage.sh random-uuid)

bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties

bin/kafka-server-start.sh -daemon config/kraft/server.properties

bin/kafka-topics.sh --create --topic quickstart-events --bootstrap-server localhost:9092

bin/kafka-console-producer.sh --topic quickstart-events --bootstrap-server localhost:9092