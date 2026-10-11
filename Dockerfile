# Use an official Node runtime as a parent image
FROM node:24-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your app code
COPY . .

# Expose the port your app runs on
EXPOSE 3000

# Command to run your app
CMD ["node", "index.js"]