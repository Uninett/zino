=================================
How to: Use the Zino Docker image
=================================

The repository includes a Dockerfile and a docker-compose file.
You can use these to build and run the Zino application as a Docker container.
The following steps show how to get started:

1. **Build the Docker Image**:

   If you have the Zino source code and Dockerfile in the current directory,
   you can build the Docker image locally.
   This is done using the `docker-compose` command:

   .. code:: shell

      docker-compose build

   This command will build the Docker image with the tag `zino:latest`.

2. **Run the Docker Container**:

   Once the image is built, you can run the Zino container using `docker-compose`:

   .. code:: shell

      docker-compose up

   This will start the Zino container,
   exposing necessary ports as configured in the docker-compose file.

3. **Configuration Files**:

   The `docker-compose` file is configured to mount the current directory (`./`)
    into the `/zino` directory inside the container. 
   Ensure that the current directory contains all necessary Zino configuration files.

4. **Port Mapping**:

   The `docker-compose` file maps the following ports by default:
   - Port `162` (Default trap port)
   - Port `8001` (API port)
   - Port `8002` (Notification port)

   If you wish to specify the trap port, 
   uncomment and modify the `command` field in the `docker-compose` file accordingly.
   For example:

   .. code:: yaml

      command: "--trap-port 1162"

5. **External Image Option**:

   If you do not wish to build the image locally, 
   you can instead use the pre-built image available on GitHub Container Registry. 
   To do this, comment out the `build` and `image: zino:latest` lines in the `docker-compose` file,
   and uncomment the following line:

   .. code:: yaml

      image: ghcr.io/uninett/zino:latest

   This will fetch the latest Zino image from the external registry.

