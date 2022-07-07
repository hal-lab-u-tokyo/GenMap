FROM centos:8

# system update
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-Linux-*
RUN sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-Linux-*
RUN dnf -y update && dnf clean all

LABEL maintainer="Takuya Kojima <tkojima@am.ics.keio.ac.jp>"

RUN echo "installing python3.6 and required packages"
RUN dnf -y groupinstall "Development Tools"
RUN dnf -y install git python36 python36-devel python3-libs python3-tkinter graphviz cmake

RUN echo "installing python packages"
RUN pip3 install pyparsing==3.0.1
RUN pip3 install numpy==1.18.1
RUN pip3 install deap==1.0.1
RUN pip3 install matplotlib==3.0.0
RUN pip3 install networkx==2.3
RUN pip3 install prettytable==0.7.2
RUN pip3 install PuLP==2.4
RUN pip3 install pydot==1.4.1
RUN pip3 install pygmo==2.9
RUN pip3 install tqdm==4.31.1
RUN pip3 install cvxpy==1.1.10
RUN pip3 install seaborn==0.11.1
RUN pip3 install llvmlite==0.30.0
RUN pip3 install pyeda==0.28.0
RUN pip3 install mosek==9.2.38

RUN echo "cloning GenMap repogitory"
RUN git clone https://github.com/hungalab/GenMap.git /opt/GenMap

RUN echo 'export GENMAP_HOME="/opt/GenMap"' >> /etc/profile
RUN echo 'alias genmap="python3 ${GENMAP_HOME}/GenMap.py"' >> /etc/profile

CMD ["/bin/bash", "--login"]
