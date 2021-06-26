## Pull docker image
You can pull a pre-built docker image from DockerHub.
```
$ docker pull tkojima0107/genmap
```

Of course, this repository contains Dockerfile.
So, you can also build the same image on your machine as follows:
```
$ cd GenMap/docker
$ docker build -t {image name} .
```

## Run docker container

A container will be started by the following commands.
GenMap includes a mapping visualization.
In order to show the GUI in host machine,
xhost command, DISPLAY environment variable, and the two volume mounting are needed to connect X-Window server from the container.

```
$ xhost + local:docker
$ docker run  -it --network=host \
	-e DISPLAY=$DISPLAY \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	-v $HOME/.Xauthority:/root/.Xauthority \
	{image name}
```
In this docker image, GenMap repository is cloned at `/opt/GenMap`.
`GENMAP_HOME` enviroment variable is available in the shell.
Besides, `genmap` alias is already set so you can start the mapping optimization as the following command.

```
$ genmap application_DFG operation_frequency [--nproc num]
```

After running the container, it is better to re-enable the access control.
```
$ xhost - local:docker
```

