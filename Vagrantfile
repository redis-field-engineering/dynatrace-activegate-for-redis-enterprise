# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box      = "ubuntu/focal64"
  config.vm.hostname = "dynatrace"
  config.vm.provider "virtualbox" do |v|
  config.vm.boot_timeout = 600
    v.memory = 3072
    v.cpus = 2
  end

 config.vm.provision "shell" do |s|
  s.inline = "/usr/bin/apt-get update && /usr/bin/apt-get install -y python3-apt"
  end


  config.vm.provision "ansible" do |ansible|
    ansible.playbook   = "ansible/playbook.yml"
    ansible.extra_vars = { ansible_python_interpreter:"/usr/bin/python3" }
  end
end
