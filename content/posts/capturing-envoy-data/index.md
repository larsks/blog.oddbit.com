---
categories: [tech]
aliases: ["/2012/02/22/capturing-envoy-data/"]
title: Capturing Envoy Data
date: "2012-02-22"
---

Pursuant to my [last post][1], I've written a simple man-in-the-middle proxy to intercept communication between the Envoy and the Enphase servers. The code is available [here][2].  
  
## What it does
  
As I detailed in my previous post, the Envoy sends data to Enphase via http `POST` requests. The proxy intercepts these requests, extracts the XML data from the request, and writes it to a local file (by default in `/var/spool/envoy`). It then forwards the request on to Enphase, and returns the reply to your Envoy.  
  
In addition to extracting the XML data, the proxy also logs the complete contents (headers and message content) of the request and the reply to files.  

## How it works
  
Out of the box, your Envoy configures itself automatically using DHCP. Possibly, you've configured it statically. In either case, it will typically be configured to connect via your default gateway -- generally, your home router, cable modem, etc. In order to intercept the communication between the Envoy and Enphase, we insert another server between the Envoy and your network gateway. In the foollowing diagram, the dotted line represents the original communication path, while the solid lines represent the new communication path:  

![envoy communication][3]

The intermediate system -- which we'll call the interceptor -- will use a few tricks to redirect traffic destined for Enphase to the local proxy (which will log the data locally and then forward it on to Enphase).  

## Assumptions

For the purposes of this article, we'll assume that your Envoy is at address 192.168.1.100, and the address of the interceptor is 192.168.1.200.  
  
I'm assuming that your interceptor is running Linux. It may be possible to accomplish the same thing with other tools, but I'm relying on the Linux netfilter subsystem (aka "iptables") to perform certain key tasks.  

## Configuring the Envoy

You will need to congfigure the Envoy to use your interceptor host as its default gateway.  

1. Go to the [network connectivity][5] page on your Envoy.
2. If it's checked, uncheck the "Use DHCP" setting and select the "Updating DHCP setting" button.
3. Set the "Gateway IP" field to the address of your interceptor (192.168.1.200 in this example).
4. Select the "Update Interface 0" button.

## Configuring the interceptor

### Redirecting requests

We need to configure the interceptor to redirect requests to the Enphase servers to a local application. We'll add the following firewall rule:  

    iptables -t nat -A PREROUTING -s 192.168.1.100 -p tcp \
      --dport 443 -j REDIRECT --to-ports 4430
    
This rule matches https (port 443) requests from your Envoy (192.168.1.100) and redirects them to port 4430 on the interceptor.  
Note that this rule will be lost if you reboot your system. Making firewall rules persistent is beyond the scope of this article; consult the documentation for your distribution of choice.  
  
### Handling SSL

My simple Python proxy doesn't speak SSL, so we need to create a plain http request from the https request. Normally this would be difficult, but Enphase has made our life easier by not checking the validity of the SSL certificate. We're going to use [stunnel][6] as an https-to-http proxy. Create a file called /etc/stunnel/envoy-ssl.conf with the following contents:  

    [https_in]
    accept = 4430
    cert = /etc/pki/tls/certs/localhost.crt
    connect = 127.0.0.1:8080
    
Run stunnel with this configuration:  
    
    stunnel /etc/stunnel/envoy-ssl.conf
 
This assumes you have an SSL certificate in /etc/pki/tls/certs/localhost.crt. You will probably need to generate one, which again is left as an exercise to the reader.  
  
### Installing bottle

The proxy relies on the [bottle][7] Python web framework, which is probably not installed on your system. The easiest way to get things going is to install a Python "virtual environment" with the appropriate modules. Create a new virtual environment:
    
    virtualenv ~/env/envoy
    
And install bottle:
    
    ~/env/envoy/bin/pip install bottle

### Creating directories

By default the proxy will write data to /var/spool/envoy. You'll need to make sure this directory exists and is writable by whatever account you're using to run the proxy.

## Running the proxy

Now that you've got all the prerequisites in place, you should be able to start the proxy by running:
    
    ~/env/envoy/bin/python proxy.py
    
You should see something like this:
    
    Bottle server starting up (using WSGIRefServer())...
    Listening on http://127.0.0.1:8080/
    Hit Ctrl-C to quit.

Assuming that everything else went as planned, sometime within the next five minutes you should see the proxy service a request from your Envoy:

    localhost.localdomain - - [22/Feb/2012 09:03:57] "POST /emu_reports/
    performance_report?webcomm_version=3.0 HTTP/1.1" 200 103
    
From this request you will end up with three files in /var/spool/envoy:

- `2012-02-22T09:03:01-0j1FFs.xml`  
  This is the XML data from the Envoy and is probably the most interesting file.

- `2012-02-22T09:03:01-ZMxw6b.request`  
  This is the raw request from the Envoy.

- `2012-02-22T09:03:02-NB4DbR.response`   
  This is the response from the Enphase servers.

If you find some bugs, please let me know by creating a new issue [here][8]. Note that this is only for bugs in the code; if you need basic networking tutorials and so forth the Google has lots of help for you.

[1]: http://blog.oddbit.com/2012/02/13/enphase-envoy-xml-data-format/
[2]: https://github.com/larsks/envoy-tools
[3]: envoy-capture.png
[5]: http://192.168.1.100/admin/lib/network_display?locale=en
[6]: http://www.stunnel.org/
[7]: http://bottlepy.org/
[8]: https://github.com/larsks/envoy-tools/issues

