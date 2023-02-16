---
aliases:
- /2014/11/15/creating-a-windows-image-for-openstack/
- /post/2014-11-15-creating-a-windows-image-for-openstack
categories:
- tech
date: '2014-11-15'
tags:
- openstack
- windows
title: Creating a Windows image for OpenStack
---

If you want to build a Windows image for use in your OpenStack
environment, you can follow [the example in the official
documentation][docs-windows-image], or you can grab a Windows 2012r2
evaluation [pre-built image][] from the nice folks at [CloudBase][].

[docs-windows-image]: http://docs.openstack.org/image-guide/content/windows-image.html
[pre-built image]: http://www.cloudbase.it/ws2012r2/
[cloudbase]: http://www.cloudbase.it/

The CloudBase-provided image is built using a set of scripts and
configuration files that CloudBase has [made available on
GitHub][imaging-tools].

[imaging-tools]: https://github.com/cloudbase/windows-openstack-imaging-tools/

The CloudBase repository is an excellent source of information, but I
wanted to understand the process myself. This post describes the
process I went through to establish an automated process for
generating a Windows image suitable for use with OpenStack.

<!-- more -->

## Unattended windows installs

The Windows installer supports [fully automated installations][] through
the use of an answer file, or "unattend" file, that provides
information to the installer that would otherwise be provided
manually.  The installer will look in [a number of places][] to find
this file.  For our purposes, the important fact is that the installer
will look for a file named `autounattend.xml` in the root of all
available read/write or read-only media.  We'll take advantage of this
by creating a file `config/autounattend.xml`, and then generating an
ISO image like this:

    mkisofs -J -r -o config.iso config

And we'll attach this ISO to a vm later on in order to provide the
answer file to the installer.

[fully automated installations]: http://technet.microsoft.com/en-us/library/ff699026.aspx
[a number of places]: http://technet.microsoft.com/en-us/library/cc749415%28v=ws.10%29.aspx

So, what goes into this answer file?

The answer file is an XML document enclosed in an
`<unattend>..</unattend>` element.  In order to provide all the
expected XML namespaces that may be used in the document, you would
typically start with something like this:

    <?xml version="1.0" ?>
    <unattend
      xmlns="urn:schemas-microsoft-com:unattend"
      xmlns:ms="urn:schemas-microsoft-com:asm.v3"
      xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">

      <!-- your content goes here -->

    </unattend>

Inside this `<unattend>` element you will put one or more `<settings>`
elements, corresponding to the different [configuration passes][] of the
installer:

[configuration passes]: http://technet.microsoft.com/en-us/library/cc766245%28v=ws.10%29.aspx

    <settings pass="specialize">
    </settings>

The available configuration passes are:

- [auditSystem][]
- [auditUser][]
- [generalize][]
- [offlineServicing][]
- [oobeSystem][]
- [specialize][]
- [windowsPE][]

[auditSystem]: http://technet.microsoft.com/en-us/library/cc749062%28v=ws.10%29.aspx
[auditUser]: http://technet.microsoft.com/en-us/library/cc722343%28v=ws.10%29.aspx
[generalize]: http://technet.microsoft.com/en-us/library/cc766229%28v=ws.10%29.aspx
[offlineServicing]: http://technet.microsoft.com/en-us/library/cc749001%28v=ws.10%29.aspx
[oobeSystem]: http://technet.microsoft.com/en-us/library/cc748990%28v=ws.10%29.aspx
[specialize]: http://technet.microsoft.com/en-us/library/cc722130%28v=ws.10%29.aspx
[windowsPE]: http://technet.microsoft.com/en-us/library/cc766028%28v=ws.10%29.aspx

Of these, the most interesting for our use will be:

- `windowsPE` -- used to install device drivers for use within the
  installer environment.  We will use this to install the VirtIO
  drivers necessary to make VirtIO devices visible to the Windows
  installer.

- `specialize` -- In this pass, the installer applies machine-specific
  configuration.  This is typically used to configure networking,
  locale settings, and most other things.

- `oobeSystem` -- In this pass, the installer configures things that
  happen at first boot.  We use this to step to install some
  additional software and run [sysprep][] in order to prepare the
  image for use in OpenStack.

[sysprep]: http://technet.microsoft.com/en-us/library/cc721940%28v=ws.10%29.aspx

Inside each `<settings>` element we will place one or more
`<component>` elements that will apply specific pieces of
configuration.  For example, the following `<component>` configures
language and keyboard settings in the installer:

    <settings pass="windowsPE">
      <component name="Microsoft-Windows-International-Core-WinPE"
        processorArchitecture="amd64"
        publicKeyToken="31bf3856ad364e35"
        language="neutral"
        versionScope="nonSxS">

        <SetupUILanguage>
          <UILanguage>en-US</UILanguage>
        </SetupUILanguage>
        <InputLocale>en-US</InputLocale>
        <UILanguage>en-US</UILanguage>
        <SystemLocale>en-US</SystemLocale>
        <UserLocale>en-US</UserLocale>
      </component>
    </settings>

[Technet][] provides documentation on the [available components][].

[technet]: http://technet.microsoft.com/
[available components]: http://technet.microsoft.com/en-us/library/ff699038.aspx

## Cloud-init for Windows

[Cloud-init][] is a tool that will configure a virtual instance when
it first boots, using metadata provided by the cloud service provider.
For example, when booting a Linux instance under OpenStack,
`cloud-init` will contact the OpenStack metadata service at
http://169.254.169.254/ in order to retrieve things like the system
hostname, SSH keys, and so forth.

[cloud-init]: http://cloudinit.readthedocs.org/en/latest/

While `cloud-init` has support for Linux and BSD, it does not support
Windows.  The folks at [Cloudbase][] have produced [cloudbase-init][]
in order to fill this gap.  Once installed, the `cloudbase-init` tool
will, upon first booting a system:

[cloudbase]: http://www.cloudbase.it/
[cloudbase-init]: http://www.cloudbase.it/cloud-init-for-windows-instances/

- Configure the network using information provided in the cloud
  metadata
- Set the system hostname
- Create an initial user account (by default "Admin") with a randomly
  generated password (see below for details)
- Install your public key, if provided
- Execute a script provided via cloud `user-data`

### Passwords and ssh keys

While `cloudbase-init` will install your SSH public key (by default
into `/Users/admin/.ssh/authorized_keys`), Windows does not ship with
an SSH server and cloudbase-init does not install one.  So what is it
doing with the public key?

While you could arrange to install an ssh server that would make use
of the key, `cloudbase-init` uses it for a completely unrelated
purpose: encrypting the randomly generated password.  This encrypted
password is then passed back to OpenStack, where you can retrieve it
using the `nova get-password` command, and decrypt it using the
corresponding SSH private key.

Running `nova get-password myinstance` will return something like:

    w+In/P6+FeE8nv45oCjc5/Bohq4adqzoycwb9hOy9dlmuYbz0hiV923WW0fL
    7hvQcZnWqGY7xLNnbJAeRFiSwv/MWvF3Sq8T0/IWhi6wBhAiVOxM95yjwIit
    /L1Fm0TBARjoBuo+xq44YHpep1qzh4frsOo7TxvMHCOtibKTaLyCsioHjRaQ
    dHk+uVFM1E0VIXyiqCdj421JoJzg32DqqeQTJJMqT9JiOL3FT26Y4XkVyJvI
    vtUCQteIbd4jFtv3wEErJZKHgxHTLEYK+h67nTA4rXpvYVyKw9F8Qwj7JBTj
    UJqp1syEqTR5/DUHYS+NoSdONUa+K7hhtSSs0bS1ghQuAdx2ifIA7XQ5eMRS
    sXC4JH3d+wwtq4OmYYSOQkjmpKD8s5d4TgtG2dK8/l9B/1HTXa6qqcOw9va7
    oUGGws3XuFEVq9DYmQ5NF54N7FU7NVl9UuRW3WTf4Q3q8VwJ4tDrmFSct6oG
    2liJ8s7ybbW5PQU/lJe0gGBGGFzo8c+Rur17nsZ01+309JPEUKqUQT/uEg55
    ziOo8uAwPvInvPkbxjH5doH79t47Erb3cK44kuqZy7J0RdDPtPr2Jel4NaSt
    oCs+P26QF2NVOugsY9O/ugYfZWoEMUZuiwNWCWBqrIohB8JHcItIBQKBdCeY
    7ORjotJU+4qAhADgfbkTqwo=

Providing your secret key as an additional parameter will decrypt the
password:

    $ nova get-password myinstance ~/.ssh/id_rsa
    fjgJmUB7fXF6wo

With an appropriately configured image, you could connect using an RDP
client and log in as the "Admin" user using that password.

### Passwords without ssh keys

If you do not provide your instance with an SSH key you will not be
able to retrieve the randomly generated password.  However, if you can
get console access to your instance (e.g., via the Horizon dashboard),
you can log in as the "Administrator" user, at which point you will be
prompted to set an initial password for that account.

### Logging

You can find logs for `cloudbase-init` in `c:\program files
(x86)\cloudbase solutions\cloudbase-init\log\cloudbase-init.log`.

If appropriately configured, `cloudbase-init` will also log to the
virtual serial port.  This log is available in OpenStack by running
`nova console-log <instance>`.  For example:

    $ nova console-log my-windows-server
    2014-11-19 04:10:45.887 1272 INFO cloudbaseinit.init [-] Metadata service loaded: 'HttpService'
    2014-11-19 04:10:46.339 1272 INFO cloudbaseinit.init [-] Executing plugin 'MTUPlugin'
    2014-11-19 04:10:46.371 1272 INFO cloudbaseinit.init [-] Executing plugin 'NTPClientPlugin'
    2014-11-19 04:10:46.387 1272 INFO cloudbaseinit.init [-] Executing plugin 'SetHostNamePlugin'
    .
    .
    .

## Putting it all together

I have an [install script][] that drives the process, but it's
ultimately just a wrapper for `virt-install` and results in the
following invocation:

[install script]: https://github.com/larsks/windows-openstack-image/blob/master/install

    exec virt-install -n ws2012 -r 2048 \
      -w network=default,model=virtio \
      --disk path=$TARGET_IMAGE,bus=virtio \
      --cdrom $WINDOWS_IMAGE \
      --disk path=$VIRTIO_IMAGE,device=cdrom \
      --disk path=$CONFIG_IMAGE,device=cdrom \
      --os-type windows \
      --os-variant win2k8 \
      --vnc \
      --console pty

Where `TARGET_IMAGE` is the name of a pre-existing `qcow2` image onto
which we will install Windows, `WINDOWS_IMAGE` is the path to an ISO
containing Windows Server 2012r2, `VIRTIO_IMAGE` is the path to an ISO
containing VirtIO drivers for Windows (available from the [Fedora
project][]), and `CONFIG_IMAGE` is a path to the ISO containing our
`autounattend.xml` file.

[fedora project]: https://alt.fedoraproject.org/pub/alt/virtio-win/latest/images/bin/

The fully commented [autounattend.xml][] file, along with the script
mentioned above, are available in my [windows-openstack-image][]
repository on GitHub.

[autounattend.xml]: https://github.com/larsks/windows-openstack-image/blob/master/config/autounattend.xml
[windows-openstack-image]: https://github.com/larsks/windows-openstack-image/

## The answer file in detail

### windowsPE

In the [windowsPE][] phase, we start by configuring the installer locale
settings:

    <component name="Microsoft-Windows-International-Core-WinPE"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS">

      <SetupUILanguage>
        <UILanguage>en-US</UILanguage>
      </SetupUILanguage>
      <InputLocale>en-US</InputLocale>
      <UILanguage>en-US</UILanguage>
      <SystemLocale>en-US</SystemLocale>
      <UserLocale>en-US</UserLocale>

    </component>

And installing the VirtIO drviers using the [Microsoft-Windows-PnpCustomizationsWinPE][] component:

[Microsoft-Windows-PnpCustomizationsWinPE]: http://technet.microsoft.com/en-us/library/ff715623.aspx

    <component name="Microsoft-Windows-PnpCustomizationsWinPE"
      publicKeyToken="31bf3856ad364e35" language="neutral"
      versionScope="nonSxS" processorArchitecture="amd64">

      <DriverPaths>
        <PathAndCredentials wcm:action="add" wcm:keyValue="1">
          <Path>d:\win8\amd64</Path>
        </PathAndCredentials>
      </DriverPaths>

    </component>

This assumes that the VirtIO image is mounted as drive `d:`.

With the drivers installed, we can then call the
[Microsoft-Windows-Setup][] component to configure the disks and
install Windows.  We start by configuring the product key:

[Microsoft-Windows-Setup]: http://technet.microsoft.com/en-us/library/ff715827.aspx

    <component name="Microsoft-Windows-Setup"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS"
      processorArchitecture="amd64">

      <UserData>
        <AcceptEula>true</AcceptEula>
        <ProductKey>
          <WillShowUI>OnError</WillShowUI>
          <Key>INSERT-PRODUCT-KEY-HERE</Key>
        </ProductKey>
      </UserData>

And then configure the disk with a single partition (that will grow to
fill all the available space) which we then format with NTFS:

      <DiskConfiguration>
        <WillShowUI>OnError</WillShowUI>
        <Disk wcm:action="add">
          <DiskID>0</DiskID>
          <WillWipeDisk>true</WillWipeDisk>

          <CreatePartitions>
            <CreatePartition wcm:action="add">
              <Order>1</Order>
              <Extend>true</Extend>
              <Type>Primary</Type>
            </CreatePartition>
          </CreatePartitions>

          <ModifyPartitions>
            <ModifyPartition wcm:action="add">
              <Format>NTFS</Format>
              <Order>1</Order>
              <PartitionID>1</PartitionID>
              <Label>System</Label>
            </ModifyPartition>
          </ModifyPartitions>
        </Disk>
      </DiskConfiguration>

We provide information about what to install:

      <ImageInstall>
        <OSImage>
          <WillShowUI>Never</WillShowUI>

          <InstallFrom>
            <MetaData>
              <Key>/IMAGE/Name</Key>
              <Value>Windows Server 2012 R2 SERVERSTANDARDCORE</Value>
            </MetaData>
          </InstallFrom>

And where we would like it installed:

          <InstallTo>
            <DiskID>0</DiskID>
            <PartitionID>1</PartitionID>
          </InstallTo>
        </OSImage>
      </ImageInstall>

### specialize

In the [specialize][] phase, we start by setting the system name to a
randomly generated value using the [Microsoft-Windows-Shell-Setup][]
component:

[Microsoft-Windows-Shell-Setup]: http://technet.microsoft.com/en-us/library/ff715801.aspx

    <component name="Microsoft-Windows-Shell-Setup"
      publicKeyToken="31bf3856ad364e35" language="neutral"
      versionScope="nonSxS" processorArchitecture="amd64">
      <ComputerName>*</ComputerName>
    </component>

We enable remote desktop because in an OpenStack environment this will
probably be the preferred mechanism with which to connect to the host
(but see [this document][winrm] for an alternative mechanism).

[winrm]: http://www.cloudbase.it/windows-without-passwords-in-openstack/

First, we need to permit terminal server connections:

    <component name="Microsoft-Windows-TerminalServices-LocalSessionManager"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS">
      <fDenyTSConnections>false</fDenyTSConnections>
    </component>

And we do not want to require network-level authentication prior to
connecting:

    <component name="Microsoft-Windows-TerminalServices-RDP-WinStationExtensions"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS">
      <UserAuthentication>0</UserAuthentication>
    </component>

We will also need to open the necessary firewall group:

    <component name="Networking-MPSSVC-Svc"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS">
      <FirewallGroups>
        <FirewallGroup wcm:action="add" wcm:keyValue="RemoteDesktop">
          <Active>true</Active>
          <Profile>all</Profile>
          <Group>@FirewallAPI.dll,-28752</Group>
        </FirewallGroup>
      </FirewallGroups>
    </component>

Finally, we use the [Microsoft-Windows-Deployment][] component to configure the Windows firewall to permit ICMP traffic:

[Microsoft-Windows-Deployment]: http://technet.microsoft.com/en-us/library/ff716283.aspx

    <component name="Microsoft-Windows-Deployment"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral" versionScope="nonSxS">

      <RunSynchronous>

        <RunSynchronousCommand wcm:action="add">
          <Order>3</Order>
          <Path>netsh advfirewall firewall add rule name=ICMP protocol=icmpv4 dir=in action=allow</Path>
        </RunSynchronousCommand>


And to download the `cloudbase-init` installer and make it available
for later steps:

        <RunSynchronousCommand wcm:action="add">
          <Order>5</Order>
          <Path>powershell -NoLogo -Command "(new-object System.Net.WebClient).DownloadFile('https://www.cloudbase.it/downloads/CloudbaseInitSetup_Beta_x64.msi', 'c:\Windows\Temp\cloudbase.msi')"</Path>
        </RunSynchronousCommand>
      </RunSynchronous>
    </component>

We're using [Powershell][] here because it has convenient methods
available for downloading URLs to local files.  This is roughly
equivalent to using `curl` on a Linux system.

[powershell]: http://technet.microsoft.com/en-us/scriptcenter/powershell.aspx

### oobeSystem

In the [oobeSystem][] phase, we configure an automatic login for the
Administrator user:

      <UserAccounts>
        <AdministratorPassword>
          <Value>Passw0rd</Value>
          <PlainText>true</PlainText>
        </AdministratorPassword>
      </UserAccounts>
      <AutoLogon>
        <Password>
          <Value>Passw0rd</Value>
          <PlainText>true</PlainText>
        </Password>
        <Enabled>true</Enabled>
        <LogonCount>50</LogonCount>
        <Username>Administrator</Username>
      </AutoLogon>

This automatic login only happens once, because we configure
`FirstLogonCommands` that will first install `cloudbase-init`:

      <FirstLogonCommands>
        <SynchronousCommand wcm:action="add">
          <CommandLine>msiexec /i c:\windows\temp\cloudbase.msi /qb /l*v c:\windows\temp\cloudbase.log LOGGINGSERIALPORTNAME=COM1</CommandLine>
          <Order>1</Order>
        </SynchronousCommand>

And will then run `sysprep` to generalize the system (which will,
among other things, lose the administrator password):

        <SynchronousCommand wcm:action="add">
          <CommandLine>c:\windows\system32\sysprep\sysprep /generalize /oobe /shutdown</CommandLine>
          <Order>2</Order>
        </SynchronousCommand>
      </FirstLogonCommands>

The system will shut down when `sysprep` is complete, leaving you with a
Windows image suitable for uploading into OpenStack:

    glance image-create --name ws2012 \
      --disk-format qcow2 \
      --container-format bare  \
      --file ws2012.qcow2

## Troubleshooting

If you run into problems with an unattended Windows installation:

During the first stage of the installer, you can look in the
`x:\windows\panther` directory for `setupact.log` and `setuperr.log`,
which will have information about the early install process.  The `x:`
drive is temporary, and files here will be discarded when the system
reboots.

Subsequent installer stages will log to
`c:\windows\panther\`.

If you are unfamiliar with Windows, the `type` command can be used
very much like the `cat` command on Linux, and the `more` command
provides paging as you would expect.  The `notepad` command will open
a GUI text editor/viewer.

You can emulate the `tail` command using `powershell`; to see the last
10 lines of a file:

    C:\> powershell -command "Get-Content setupact.log -Tail 10"

Technet has a [Deployment Troubleshooting and Log Files][logfiles]
document that discusses in more detail what is logged and where to
find it.

[logfiles]: http://technet.microsoft.com/en-us/library/hh825073.aspx