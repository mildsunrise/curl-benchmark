# curl-benchmark

Simple Python script that runs `curl` many times, telling it to report time metrics
until you press Control+C. These metrics are printed in a colored fashion and then
processed to extract average time spent in each phase (DNS lookup, TCP connection,
TLS handshake, TTFB...).

![Standard usage](https://i.imgur.com/PE8VkPw.png)

Because it's just spawning `curl`, you can pass arbitrary options to curl by putting
them after `--`. Here we're using `--compressed --tcp-nodelay` to resemble a browser
more closely:

![cURL options](https://i.imgur.com/tEpok2f.png)

The `-r` option can be used to hide the raw metrics and only produce the report,
and is useful together with `-n`:

![Report mode](https://i.imgur.com/RfFYLj1.png)

Remember that if you pass options to curl, the URL must go last.

## Usage

It's a Python script without dependencies. Just run it.  
You need to have Python 3 and cURL installed.  
Use `-h` or `--help` to get help.

## Drawbacks

cURL has lots of options, and some of them significantly affect the time metrics:

 - `--compressed` allows the server to send a compressed version of the asset,
   reducing content download time in that case.

 - Having (and using) HTTP/2 support compiled in cURL can speed up TTFB and
   download sometimes.

 - `--false-start` is a feature of TLS that allows the handshake to 'complete' in
   2RTT instead of the usual 3. So it speeds the handshake by 1RTT.

 - `--tcp-nodelay` supresses queuing of data to be sent, and significantly speeds
   up the TLS handshake and sometimes the TTFB.

Ideally, if you want to resemble a browser when it comes to time metrics, you should
at least use the first three, and a lot of browsers also use the fourth. The problem
is that ATM `--false-start` is *not* supported unless cURL was compiled with NSS.
So you'll have to account for that when interpreting the metrics.

## Fixes, improvements, requests

They're welcome! There isn't much code quality yet, though, however you're free to
hack it to your needs.
