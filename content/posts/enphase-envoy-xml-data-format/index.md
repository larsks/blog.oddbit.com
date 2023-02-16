---
categories: [tech]
aliases: ["/2012/02/13/enphase-envoy-xml-data-format/"]
title: Enphase Envoy XML Data Format
date: "2012-02-13"
---

We recently installed a (photovoltaic) solar array on our house.  The system uses [Enphase][1] microinverters, and includes a monitoring device called the "[Envoy][2]".  The Envoy collects data from the microinverters and sends it back to Enphase.  Enphase performs monitoring services for the array and also provides access to the data collected by the Envoy product.  
  
I'm interested in getting direct access to the data provided by the Envoy.  In pursuit of that goal, I set up a man-in-the-middle proxy server on my home network to intercept the communication from the Envoy to the Enphase servers.  I'm documenting the results of my exploration here in case somebody else finds the information useful.  
  
The Envoy sends deflate-encoded XML data to the Enphase servers. You can decompress the data using Python's `zlib` module like this:  
  

    
    import zlib
    xml_data = zlib.decompress(deflate_compressed_data)
    

  
The request is an http `POST` to [https://reports.enphaseenergy.com/emu_reports/performance_report?webcomm_version=3.0][3]. The request headers look like this:  
  

    
    POST /emu_reports/performance_report?webcomm_version=3.0 HTTP/1.1
    Accept: */*
    Connection: close
    Content-Type: application/x-deflate
    Content-Length: 729
    Host: reports.enphaseenergy.com:443
    

  
The request body -- after inflating it -- looks something like this:  
  

    
    <?xml version='1.0' encoding='utf-8'?>
    <perf_report report_timestamp='1329134202'>
      <envoy ip_addr='192.168.1.166' mac_addr='00:11:22:33:44:55'
      timezone='US/Eastern' part_num='800-00024-r04'
      sw_version='R3.0.0 (9720d7)' serial_num='123456115374' />
      <event correlation_id='161' event_state='1' id='221'
      event_code='10009' eqid='123456102635' serial_num='123456102635'
      event_date='1329134118' />
      <event correlation_id='194' event_state='1' id='222'
      event_code='101' eqid='123456103685.1' serial_num='123456103685'
      event_date='1329134119' />
      <event correlation_id='196' event_state='1' id='223'
      event_code='101' eqid='123456105331.1' serial_num='123456105331'
      event_date='1329134120' />
      <event correlation_id='202' event_state='1' id='224'
      event_code='101' eqid='123456103294.1' serial_num='123456103294'
      event_date='1329134130' />
      <event correlation_id='206' event_state='1' id='225'
      event_code='101' eqid='123456105321.1' serial_num='123456105321'
      event_date='1329134139' />
      <event event_state='2' id='226' event_code='101'
      eqid='123456104335.1' serial_num='123456104335'
      event_date='1329134152' />
      <event event_state='0' id='227' event_code='509'
      eqid='123456104335' serial_num='123456104335'
      event_date='1329134152' />
      <event correlation_id='213' event_state='1' id='228'
      event_code='101' eqid='123456105296.1' serial_num='123456105296'
      event_date='1329134153' />
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105041' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456105041.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456104335' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456104335.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456104246' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456104246.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456104224' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456104224.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456102776' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456102776.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456103271' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456103271.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105190' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456105190.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105321' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456105321.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105178' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456105178.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456104988' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456104988.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456103294' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456103294.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105346' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456105346.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105297' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456105297.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456104896' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456104896.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105331' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456105331.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456103546' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456103546.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456103685' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456103685.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2359296' part_num='800-00103-r05'
      observed_flags='0' eqid='123456103215' control_bits='0'>
        <channel channel_type='1' condition_flags='16'
        observed_flags='0' eqid='123456103215.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456102635' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456102635.1' control_bits='0' />
      </device>
      <device image_bits='131072' device_type='1' admin_state='1'
      condition_flags='2097152' part_num='800-00103-r05'
      observed_flags='0' eqid='123456105296' control_bits='0'>
        <channel channel_type='1' condition_flags='0'
        observed_flags='0' eqid='123456105296.1' control_bits='0' />
      </device>
    </perf_report>
    

  
The response headers look like this:  
  

    
    HTTP/1.1 200 OK
    Date: Mon, 13 Feb 2012 11:56:48 GMT
    Server: Apache
    X-Powered-By: Phusion Passenger (mod_rails/mod_rack) 3.0.11
    ETag: "95bc2eaddfac613540f469946f28af4b"
    X-Runtime: 297
    Cache-Control: private, max-age=0, must-revalidate
    Content-Length: 142
    Status: 200
    Cache-Control: max-age=31536000
    Expires: Tue, 12 Feb 2013 11:56:48 GMT
    Connection: close
    Content-Type: application/x-deflate; charset=utf-8
    

  
And the response body -- after inflating it -- looks something like this:  
  

    
    <?xml version="1.0" encoding="UTF-8"?>
    <perf_report_response status="success">
      <events_processed>
        <event id="221"/>
        <event id="222"/>
        <event id="223"/>
        <event id="224"/>
        <event id="225"/>
        <event id="226"/>
        <event id="227"/>
        <event id="228"/>
      </events_processed>
    </perf_report_response>
    

  
My goal is to set up a simple proxy that in addition to passing the information along to Enphase will also collect it locally. I'll update the blog if I make progress on that front.  


[1]: http://enphase.com/
[2]: http://enphase.com/products/envoy/
[3]: https://reports.enphaseenergy.com/emu_reports/performance_report?webcomm_version=3.0

