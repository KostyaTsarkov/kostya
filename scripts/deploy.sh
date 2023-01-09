#!/bin/bash
set -ex

#UBUNTU_VERSION="14.04"

setNames(){
export N1="hadoop-master"
export N2="hadoop-slave-1"
export N3="hadoop-slave-2"
export N4="hadoop-slave-3"
export CLONE=505
export VID1=401
export VID2=402
export VID3=403
export VID4=404
export IP4=10.30.1.154/24
export GW=10.30.1.254
export VLAN=310
export HDFS_PATH="/home/hadoop/hdfs"
export JAVA_PATH="/usr/lib/jvm/java-11-openjdk-amd64"
#export JAVA_FILE="java-8-openjdk-amd64"
}

launchContainers(){
pct clone $CLONE $VID4 --hostname $N1
pct set $VID4 -net0 name=eth0,bridge=vmbr0,ip=$IP4,gw=$GW,tag=$VLAN
pct start $VID4
sleep 10
}

getHostInfo(){
export HADOOP_MASTER_IP=`lxc-ls -f $VID1 | grep RUNNING | awk '{print $5}'`
export HADOOP_SLAVE1_IP=`lxc-ls -f $VID2 | grep RUNNING | awk '{print $5}'`
export HADOOP_SLAVE2_IP=`lxc-ls -f $VID3 | grep RUNNING | awk '{print $5}'`
export HADOOP_SLAVE3_IP=`lxc-ls -f $VID4 | grep RUNNING | awk '{print $5}'`
}

installUpdates(){
for hosts in $VID4
do
pct exec $hosts -- apt-get update
pct exec $hosts -- apt-get upgrade -y
pct exec $hosts -- apt-get install openjdk-11-jdk apt-transport-https ca-certificates build-essential apt-utils  ssh openssh-server wget curl -y
done
}

getHadoop(){
	# Extract all downloaded files
wget https://dlcdn.apache.org/hadoop/common/hadoop-3.3.4/hadoop-3.3.4.tar.gz -O /tmp/apps/hadoop-3.3.4.tar.gz
sleep 2
for hosts in $VID4
do
pct push $hosts /tmp/apps/hadoop-3.3.4.tar.gz /usr/local/hadoop-3.3.4.tar.gz
pct exec $hosts -- tar -xf /usr/local/hadoop-3.3.4.tar.gz -C /usr/local/
pct exec $hosts -- mv //usr/local/hadoop-3.3.4 /usr/local/hadoop
done
}


createScripts(){
	#STEP 1: Creating a User
	# Создание отдельного пользователя для Hadoop для разграничения 
	# файловой системы Unix и файловой системы Hadoop.
	# Настройка SSH необходима для выполнения различных операций на кластере.
cat > /tmp/scripts/setup-user.sh << EOF

useradd -m -s /bin/bash -G sudo hadoop
echo -e "hadoop\nhadoop" | passwd hadoop

sudo su -c "ssh-keygen -q -t rsa -f /home/hadoop/.ssh/id_rsa -N ''" hadoop
sudo su -c "cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys" hadoop

sudo su -c "mkdir -p /home/hadoop/hdfs/{namenode,datanode}" hadoop
sudo su -c "chown -R hadoop:hadoop /home/hadoop" hadoop
EOF

cat > /tmp/scripts/hosts << EOF
127.0.0.1 localhost
$HADOOP_MASTER_IP $N1
$HADOOP_SLAVE1_IP $N2
$HADOOP_SLAVE2_IP $N3
$HADOOP_SLAVE3_IP $N4
EOF

cat > /tmp/scripts/ssh.sh << EOF
sudo su -c "ssh -o 'StrictHostKeyChecking no' hadoop-slave-3 'echo 1 > /dev/null'" hadoop
sudo su -c "ssh -o 'StrictHostKeyChecking no' 0.0.0.0 'echo 1 > /dev/null'" hadoop
EOF

echo 'export JAVA_PATH="dirname $(dirname $(readlink -f $(which java)))"' > /tmp/scripts/set_java_path.sh

cat > /tmp/scripts/set_env.sh << EOF
JAVA_HOME=$JAVA_PATH
HADOOP_HOME=/usr/local/hadoop
HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop
HADOOP_MAPRED_HOME=\$HADOOP_HOME
HADOOP_COMMON_HOME=\$HADOOP_HOME
HADOOP_HDFS_HOME=\$HADOOP_HOME
YARN_HOME=\$HADOOP_HOME
PATH=\$PATH:\$JAVA_HOME/bin:\$HADOOP_HOME/sbin:\$HADOOP_HOME/bin
bash /home/hadoop/initial_setup.sh
EOF

# generate hadoop/slave files
echo "hadoop-master" > /tmp/conf/masters

cat > /tmp/conf/slaves << EOF
$N2
$N3
$N4

EOF

cat > /tmp/scripts/source.sh << EOF
sudo su -c "export JAVA_HOME=$JAVA_PATH" hadoop
sudo su -c "export HADOOP_HOME=/usr/local/hadoop" hadoop
sudo su -c "export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop " hadoop
sudo su -c "export HADOOP_MAPRED_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export HADOOP_COMMON_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export HADOOP_HDFS_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export YARN_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export PATH=\$PATH:\$JAVA_HOME/bin:\$HADOOP_HOME/sbin:\$HADOOP_HOME/bin" hadoop

cat /root/set_env.sh >> /home/hadoop/.bashrc
chown -R hadoop:hadoop /home/hadoop/

sudo su -c "source /home/hadoop/.bashrc" hadoop
EOF

cat > /tmp/scripts/hadoop.service << EOF
Unit]
Description=Hdfs service
After=network.target
[Service]
Type=forking
User=hadoop
Group=hadoop
ExecStart=/usr/local/hadoop/sbin/start-all.sh
ExecStop=/usr/local/hadoop/sbin/stop-all.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

cat > /tmp/scripts/start-hadoop.sh << EOF
sudo su -c "export JAVA_HOME=$JAVA_PATH" hadoop
sudo su -c "export HADOOP_HOME=/usr/local/hadoop" hadoop
sudo su -c "export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop " hadoop
sudo su -c "export HADOOP_MAPRED_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export HADOOP_COMMON_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export HADOOP_HDFS_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export YARN_HOME=\$HADOOP_HOME" hadoop
sudo su -c "export PATH=\$PATH:\$JAVA_HOME/bin:\$HADOOP_HOME/sbin:\$HADOOP_HOME/bin" hadoop
EOF

#echo 'sed -i "s/export JAVA_HOME=\${JAVA_HOME}/export JAVA_HOME=$JAVA_PATH/g" /usr/local/hadoop/etc/hadoop/hadoop-env.sh' > /tmp/scripts/update-java-home.sh
echo 'echo "export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64" >> /usr/local/hadoop/etc/hadoop/hadoop-env.sh' > /tmp/scripts/update-java-home.sh
echo 'chown -R hadoop:hadoop /usr/local/hadoop' >> /tmp/scripts/update-java-home.sh

echo 'echo "Executing: hadoop namenode -format: "' > /tmp/scripts/initial_setup.sh
echo 'sleep 2' >> /tmp/scripts/initial_setup.sh
echo 'hadoop namenode -format' >> /tmp/scripts/initial_setup.sh
echo 'echo "Executing: start-dfs.sh"' >> /tmp/scripts/initial_setup.sh
echo 'sleep 2' >> /tmp/scripts/initial_setup.sh
echo 'start-dfs.sh' >> /tmp/scripts/initial_setup.sh
echo 'echo "Executing: start-yarn.sh"' >> /tmp/scripts/initial_setup.sh
echo 'sleep 2' >> /tmp/scripts/initial_setup.sh
echo 'start-yarn.sh' >> /tmp/scripts/initial_setup.sh
echo "sed -i 's/bash \/home\/hadoop\/initial_setup.sh//g' /home/hadoop/.bashrc" >> /tmp/scripts/initial_setup.sh

}

generateHadoopConfig(){
# hadoop configuration
#echo "<configuration>\n  <property>\n    <name>fs.defaultFS</name>\n     <value>hdfs://$N1:8020/</value>\n  </property>\n</configuration>" > /tmp/conf/core-site.xml

cat >  /tmp/conf/core-site.xml << EOF
<configuration>
<property>
<name>fs.defaultFS</name>
<value>hdfs://$N1:8020/</value>
</property>
</configuration>
EOF

#echo "<configuration>\n  <property>\n    <name>dfs.namenode.name.dir</name>\n    <value>file:$HDFS_PATH/namenode</value>\n  </property>\n  <property>\n    <name>dfs.datanode.data.dir</name>\n    <value>file:$HDFS_PATH/datanode</value>\n  </property>\n  <property>\n    <name>dfs.replication</name>\n    <value>2</value>\n  </property>\n  <property>\n    <name>dfs.block.size</name>\n    <value>134217728</value>\n  </property>\n  <property>\n    <name>dfs.namenode.datanode.registration.ip-hostname-check</name>\n    <value>false</value>\n  </property>\n</configuration>" > /tmp/conf/hdfs-site.xml

cat > /tmp/conf/hdfs-site.xml << EOF
<configuration>
<property>
<name>dfs.namenode.name.dir</name>
<value>file:$HDFS_PATH/namenode</value>
</property>
<property>
<name>dfs.datanode.data.dir</name>
<value>file:$HDFS_PATH/datanode</value>
</property>\n  <property>\n    <name>dfs.replication</name>\n    <value>2</value>\n  </property>\n  <property>\n    <name>dfs.block.size</name>\n    <value>134217728</value>\n  </property>\n  <property>
<name>dfs.namenode.datanode.registration.ip-hostname-check</name>
<value>false</value>
</property>
</configuration>
EOF

cat > /tmp/conf/mapred-site.xml << EOF
<configuration>
<property>
<name>mapreduce.framework.name</name>
<value>yarn</value>
</property>
<property>
<name>mapreduce.jobhistory.address</name>
<value>hadoop-master:10020</value>
</property>
<property>
<name>mapreduce.jobhistory.webapp.address</name>
<value>hadoop-master:19888</value>
</property>
<property>
<name>mapred.child.java.opts</name>
<value>-Djava.security.egd=file:/dev/../dev/urandom</value>
</property>
</configuration>
EOF

cat > /tmp/conf/yarn-site.xml << EOF
<configuration>
<property>
<name>yarn.resourcemanager.hostname</name>
<value>hadoop-master</value>
</property>
<property>
<name>yarn.resourcemanager.bind-host</name>
<value>0.0.0.0</value>
</property>
<property>
<name>yarn.nodemanager.bind-host</name>
<value>0.0.0.0</value>
</property>
<property>
<name>yarn.nodemanager.aux-services</name>
<value>mapreduce_shuffle</value>
</property>
<property>
<name>yarn.nodemanager.aux-services.mapreduce_shuffle.class</name>
<value>org.apache.hadoop.mapred.ShuffleHandler</value>
</property>
<property>
<name>yarn.nodemanager.remote-app-log-dir</name>
<value>hdfs://hadoop-master:8020/var/log/hadoop-yarn/apps</value>
</property>
</configuration>
EOF
}

moveScripts(){
for hosts in $VID1 $VID2 $VID3 $VID4
do
pct push $hosts /tmp/scripts/hosts /etc/hosts
pct push $hosts /tmp/scripts/set_java_path.sh /root/set_java_path.sh
pct push $hosts /tmp/scripts/setup-user.sh /root/setup-user.sh
pct push $hosts /tmp/scripts/set_env.sh /root/set_env.sh
pct push $hosts /tmp/scripts/source.sh /root/source.sh
pct push $hosts /tmp/scripts/ssh.sh /root/ssh.sh
pct push $hosts /tmp/scripts/update-java-home.sh /root/update-java-home.sh
done
pct push $VID1 /tmp/scripts/hadoop.service /etc/systemd/system/hadoop.service
pct push $VID1 /tmp/scripts/start-hadoop.sh /root/start-hadoop.sh
}

moveHadoopConfs(){
for hosts in $VID1 $VID2 $VID3 $VID4
do
pct push $hosts /tmp/conf/masters /usr/local/hadoop/etc/hadoop/masters
pct push $hosts /tmp/conf/slaves /usr/local/hadoop/etc/hadoop/slaves
pct push $hosts /tmp/conf/core-site.xml /usr/local/hadoop/etc/hadoop/core-site.xml
pct push $hosts /tmp/conf/hdfs-site.xml /usr/local/hadoop/etc/hadoop/hdfs-site.xml
pct push $hosts /tmp/conf/mapred-site.xml /usr/local/hadoop/etc/hadoop/mapred-site.xml
pct push $hosts /tmp/conf/yarn-site.xml /usr/local/hadoop/etc/hadoop/yarn-site.xml
done
}

initJavaPath(){
for hosts in $VID4
do
pct exec $hosts -- bash /root/set_java_path.sh
done	
}

setupUsers(){
for hosts in $VID4
do
pct exec $hosts -- bash /root/setup-user.sh
done
}

configureSSH(){
for hosts in $VID4
do
pct exec $hosts -- sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/g" /etc/ssh/sshd_config
pct exec $hosts -- /etc/init.d/ssh restart
done
}

setupPasswordlessSSH(){
pct pull $VID1 /home/hadoop/.ssh/id_rsa.pub /tmp/ssh/id_rsa1.pub
pct pull $VID2 /home/hadoop/.ssh/id_rsa.pub /tmp/ssh/id_rsa2.pub
pct pull $VID3 /home/hadoop/.ssh/id_rsa.pub /tmp/ssh/id_rsa3.pub
pct pull $VID4 /home/hadoop/.ssh/id_rsa.pub /tmp/ssh/id_rsa4.pub

cat /tmp/ssh/id_rsa1.pub /tmp/ssh/id_rsa2.pub /tmp/ssh/id_rsa3.pub /tmp/ssh/id_rsa4.pub > /tmp/authorized_keys

for hosts in $VID1 $VID2 $VID3 $VID4
do
pct push $hosts /tmp/authorized_keys /home/hadoop/.ssh/authorized_keys
done
}

ensureSSH(){
for hosts in $VID4
do
pct exec $hosts -- bash /root/ssh.sh
done
}

updateJavaHome(){
for hosts in $VID4
do
pct exec $hosts -- bash /root/update-java-home.sh
done
}

executeScripts(){
for hosts in $VID4
do
pct exec $hosts -- bash /root/source.sh
pct exec $hosts -- chown -R hadoop:hadoop /usr/local/hadoop
done
}


printInstructions(){
echo "Deployment Done"
echo "---------------"
echo ""
echo "1. Access Master:"
echo " $ lxc exec hadoop-master bash"
echo ""
echo "2. Switch user to hadoop:"
echo " $ su hadoop"
echo ""
echo "With the inital login namenode will be formatted and hadoop"
echo "daemons will be started."
}

mkdirs
setNames
launchContainers
installUpdates
getHostInfo
createScripts
getHadoop
moveScripts
initJavaPath
generateHadoopConfig
moveHadoopConfs

configureSSH
setupUsers
setupPasswordlessSSH
ensureSSH
moveInitialScript
executeScripts
updateJavaHome
printInstructions
