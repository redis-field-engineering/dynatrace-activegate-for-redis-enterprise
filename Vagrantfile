# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box      = "ubuntu/trusty64"
  config.vm.hostname = "dynatrace"
  config.vm.provider "virtualbox" do |v|
  config.vm.boot_timeout = 600
    v.memory = 3072
    v.cpus = 2
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook           = "ansible/playbook.yml"
    ansible.compatibility_mode = "2.0"
  end
end
