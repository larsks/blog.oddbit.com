---
categories: [tech]
title: Packet, packet, who's got the packet?
date: "2023-02-14"
tags:
  - kernel
  - networking
  - routing
  - ebpf
  - pwru
---

In [this question](https://unix.stackexchange.com/q/735522/4989), August Vrubel has some C code that sets up a [tun][] interface and then injects a packet, but the packet seemed to disappear into the ether. In this post, I'd like to take a slightly extended look at [my answer](https://unix.stackexchange.com/a/735534/4989) because I think it's a great opportunity for learning a bit more about performing network diagnostics.

[tun]: https://docs.kernel.org/networking/tuntap.html

The original code looked like this:

{{< code language="c" title="original sendpacket.c" >}}
{{% include file="sendpacket-orig.c" %}}
{{< /code >}}

A problem with the original code is that it creates the interface, sends the packet, and tears down the interface with no delays, making it very difficult to inspect the interface configuration, perform packet captures, or otherwise figure out what's going on.

In order to resolve those issues, I added some prompts before sending the packet and before tearing down the `tun` interface (and also some minimal error checking), giving us:

{{< code language="c" title="sendpacket.c with prompts and error checking" >}}
{{% include file="sendpacket-pause.c" %}}
{{< /code >}}

We start by compiling the code:

```sh
gcc -o sendpacket sendpacket.c
```

If we try running this as a regular user, it will simply fail (which confirms that at least some of our error handling is working correctly):

```sh
$ ./sendpacket
ioctl(fd, TUNSETIFF, (void *)&ifr) (@ sendpacket-pause.c:33): Operation not permitted
```

We need to run it as `root`:

```
$ sudo ./sendpacket
interface is up
```

The `interface is up` prompt means that the code has configured the interface but has not yet sent the packet. Let's take a look at the interface configuration:

```sh
$ ip addr show tun0
3390: tun0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UNKNOWN group default qlen 500
    link/none 
    inet 172.30.0.1/32 scope global tun0
       valid_lft forever preferred_lft forever
    inet6 fe80::c7ca:fe15:5d5c:2c49/64 scope link stable-privacy 
       valid_lft forever preferred_lft forever
```

The code will emit a TCP `SYN` packet targeting address `192.168.255.8`, port `10001`. In another terminal, let's watch for that on all interfaces. If we start `tcpdump` and press RETURN at the `interface is up` prompt, we'll see something like:

```sh
# tcpdump -nn -i any port 10001
22:36:35.336643 tun0  In  IP 172.30.0.1.41626 > 192.168.255.8.10001: Flags [S], seq 2148230009, win 64240, options [mss 1460,sackOK,TS val 1534484436 ecr 0,nop,wscale 7], length 0
```

And indeed, we see the problem that was described: the packet enters the system on `tun0`, but never goes anywhere else. What's going on?

## Introducing pwru (Packet, Where are you?)

[`pwru`](https://github.com/cilium/pwru) is a nifty utility written by the folks at Cilium that takes advantage of [eBPF][] to attach traces to hundreds of kernel functions to trace packet processing through the Linux kernel. It's especially useful when packets seem to be getting dropped with no obvious explanation. Let's see what it can tell us!

[eBPF]: https://ebpf.io/

A convenient way to run `pwru` is using their official Docker image. We'll run it like this, filtering by protocol and destination port so that we only see results relating to the synthesized packet created by the `sendpacket.c` code:

```sh
docker run --privileged --rm -t --pid=host \
  -v /sys/kernel/debug/:/sys/kernel/debug/ \
  cilium/pwru --filter-proto tcp --filter-port 10001
```

If we run `sendpacket` while `pwru` is running, the output looks something like this:

```
2023/02/15 03:42:33 Per cpu buffer size: 4096 bytes
2023/02/15 03:42:33 Attaching kprobes (via kprobe-multi)...
1469 / 1469 [-----------------------------------------------------------------------------] 100.00% ? p/s
2023/02/15 03:42:33 Attached (ignored 0)
2023/02/15 03:42:33 Listening for events..
               SKB    CPU          PROCESS                     FUNC
0xffff8ce13e987900      6 [sendpacket-orig]        netif_receive_skb
0xffff8ce13e987900      6 [sendpacket-orig]   skb_defer_rx_timestamp
0xffff8ce13e987900      6 [sendpacket-orig]      __netif_receive_skb
0xffff8ce13e987900      6 [sendpacket-orig] __netif_receive_skb_one_core
0xffff8ce13e987900      6 [sendpacket-orig]                   ip_rcv
0xffff8ce13e987900      6 [sendpacket-orig]              ip_rcv_core
0xffff8ce13e987900      6 [sendpacket-orig] kfree_skb_reason(SKB_DROP_REASON_IP_CSUM)
0xffff8ce13e987900      6 [sendpacket-orig]   skb_release_head_state
0xffff8ce13e987900      6 [sendpacket-orig]               sock_wfree
0xffff8ce13e987900      6 [sendpacket-orig]         skb_release_data
0xffff8ce13e987900      6 [sendpacket-orig]            skb_free_head
0xffff8ce13e987900      6 [sendpacket-orig]             kfree_skbmem
```

And now we have a big blinking sign that tells us why the packet is being dropped:

```
0xffff8ce13e987900      6 [sendpacket-orig] kfree_skb_reason(SKB_DROP_REASON_IP_CSUM)
```

## Fixing the checksum

It looks like the synthesized packet data includes a bad checksum. We could update the code to correctly calculate the checksum...or we could just use [Wireshark][] and have it tell us the correct values. Because this isn't meant to be an IP networking primer, we'll just use Wireshark, which gives us the following updated code:

[wireshark]: https://www.wireshark.org/

```c
static void emitPacket(int tap_fd) {
  uint16_t cs;
  uint8_t packet[] = {
      0x45, 0x00, 0x00, 0x3c, 0xd8, 0x6f, 0x40, 0x00, 0x3f, 0x06, 0xf7, 0x7b,
      172,  30,   0,    1,    192,  168,  255,  8,    0xa2, 0x9a, 0x27, 0x11,
      0x80, 0x0b, 0x63, 0x79, 0x00, 0x00, 0x00, 0x00, 0xa0, 0x02, 0xfa, 0xf0,
      0x78, 0xc3, 0x00, 0x00, 0x02, 0x04, 0x05, 0xb4, 0x04, 0x02, 0x08, 0x0a,
      0x5b, 0x76, 0x5f, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x03, 0x07,
  };

  write(tap_fd, packet, sizeof(packet));
}
```

If we repeat our invocation of `pwru` and run a test with the updated code, we see:

```
2023/02/15 04:17:29 Per cpu buffer size: 4096 bytes
2023/02/15 04:17:29 Attaching kprobes (via kprobe-multi)...
1469 / 1469 [-----------------------------------------------------------------------------] 100.00% ? p/s
2023/02/15 04:17:29 Attached (ignored 0)
2023/02/15 04:17:29 Listening for events..
               SKB    CPU          PROCESS                     FUNC
0xffff8cd8a6c5ef00      9 [sendpacket-chec]        netif_receive_skb
0xffff8cd8a6c5ef00      9 [sendpacket-chec]   skb_defer_rx_timestamp
0xffff8cd8a6c5ef00      9 [sendpacket-chec]      __netif_receive_skb
0xffff8cd8a6c5ef00      9 [sendpacket-chec] __netif_receive_skb_one_core
0xffff8cd8a6c5ef00      9 [sendpacket-chec]                   ip_rcv
0xffff8cd8a6c5ef00      9 [sendpacket-chec]              ip_rcv_core
0xffff8cd8a6c5ef00      9 [sendpacket-chec]               sock_wfree
0xffff8cd8a6c5ef00      9 [sendpacket-chec]             nf_hook_slow
0xffff8cd8a6c5ef00      9 [sendpacket-chec]              nf_checksum
0xffff8cd8a6c5ef00      9 [sendpacket-chec]           nf_ip_checksum
0xffff8cd8a6c5ef00      9 [sendpacket-chec]  __skb_checksum_complete
0xffff8cd8a6c5ef00      9 [sendpacket-chec]       tcp_v4_early_demux
0xffff8cd8a6c5ef00      9 [sendpacket-chec]     ip_route_input_noref
0xffff8cd8a6c5ef00      9 [sendpacket-chec]      ip_route_input_slow
0xffff8cd8a6c5ef00      9 [sendpacket-chec]      fib_validate_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec]    __fib_validate_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec] ip_handle_martian_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec] kfree_skb_reason(SKB_DROP_REASON_NOT_SPECIFIED)
0xffff8cd8a6c5ef00      9 [sendpacket-chec]   skb_release_head_state
0xffff8cd8a6c5ef00      9 [sendpacket-chec]         skb_release_data
0xffff8cd8a6c5ef00      9 [sendpacket-chec]            skb_free_head
0xffff8cd8a6c5ef00      9 [sendpacket-chec]             kfree_skbmem
```

## Dealing with martians

Looking at the above output, we're no longer seeing the `SKB_DROP_REASON_IP_CSUM` error; instead, we're getting dropped by the routing logic:

```
0xffff8cd8a6c5ef00      9 [sendpacket-chec]      fib_validate_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec]    __fib_validate_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec] ip_handle_martian_source
0xffff8cd8a6c5ef00      9 [sendpacket-chec] kfree_skb_reason(SKB_DROP_REASON_NOT_SPECIFIED)
```

Specifically, the packet is being dropped as a "martian source", which means a packet that has a source address that is invalid for the interface on which it is being received. Unlike the previous error, we can actually get kernel log messages about this problem. If we had the `log_martians` sysctl enabled for all interfaces:

```sh
sysctl -w net.ipv4.conf.all.log_martians=1
```

Or if we enabled it specifically for `tun0` after the interface is created:

```sh
sysctl -w net.ipv4.conf.tun0.log_martians=1
```

We would see the following message logged by the kernel:

```
Feb 14 12:14:03 madhatter kernel: IPv4: martian source 192.168.255.8 from 172.30.0.1, on dev tun0
```

We're seeing this particular error because `tun0` is configured with address `172.30.0.1`, but it claims to be receiving a packet with the same source address from "somewhere else" on the network. This is a problem because we would never be able to reply to that packet (our replies would get routed to the local host). To deal with this problem, we can either change the source address of the packet, or we can change the IP address assigned to the `tun0` interface. Since changing the source address would mean mucking about with checksums again, let's change the address of `tun0`:

```c
static void bringInterfaceUp(void) {
  int sock;
  struct sockaddr_in addr = {.sin_family = AF_INET};
  struct ifreq ifr = {.ifr_name = "tun0"};

  inet_aton("172.30.0.10", &addr.sin_addr);
  memcpy(&ifr.ifr_addr, &addr, sizeof(struct sockaddr));

  sock = socket(AF_INET, SOCK_DGRAM, 0);
  must(ioctl(sock, SIOCSIFADDR, &ifr));
  must(ioctl(sock, SIOCGIFFLAGS, &ifr));
  ifr.ifr_flags |= IFF_UP | IFF_RUNNING;
  must(ioctl(sock, SIOCSIFFLAGS, &ifr));
  close(sock);
}
```

With this change, `tun0` now looks like:

```
3452: tun0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UNKNOWN group default qlen 500
    link/none 
    inet 172.30.0.10/32 scope global tun0
       valid_lft forever preferred_lft forever
    inet6 fe80::bda3:ddc8:e60e:106b/64 scope link stable-privacy 
       valid_lft forever preferred_lft forever
```

And if we repeat our earlier test in which we use `tcpdump` to watch for our synthesized packet on any interface, we now see the desired behavior:

```
# tcpdump -nn -i any port 10001
23:37:55.897786 tun0  In  IP 172.30.0.1.41626 > 192.168.255.8.10001: Flags [S], seq 2148230009, win 64240, options [mss 1460,sackOK,TS val 1534484436 ecr 0,nop,wscale 7], length 0
23:37:55.897816 eth0  Out IP 172.30.0.1.41626 > 192.168.255.8.10001: Flags [S], seq 2148230009, win 64240, options [mss 1460,sackOK,TS val 1534484436 ecr 0,nop,wscale 7], length 0
```

The packet is correctly handled by the kernel and sent out to our default gateway.

## Finishing up

The final version of the code looks like this:

{{< code language="c" title="working sendpacket.c" >}}
{{% include file="sendpacket-addr.c" %}}
{{< /code >}}
