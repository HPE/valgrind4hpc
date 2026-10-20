/******************************************************************************\
 * Socket.hpp - Socket / accept helper object
 *
 * Copyright 2015-2017,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#ifndef _SOCKET_HPP
#define _SOCKET_HPP

#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <arpa/inet.h>

class Socket {

	std::string address, port;
	int sockfd;

public:
	std::string const& getAddress() const { return address; }
	std::string const& getPort() const    { return port; }

	Socket() : sockfd(-1) {
		struct addrinfo *listener;

		// setup the hints structure
		struct addrinfo hints;
		memset(&hints, 0, sizeof(struct addrinfo));
		hints.ai_family = AF_INET;
		hints.ai_socktype = SOCK_STREAM;
		hints.ai_flags = AI_NUMERICSERV;

		// get the addrinfo on my host
		int rc;
		if ((rc = getaddrinfo(NULL, "0", &hints, &listener)) != 0)
		{
			std::ostringstream estr;
			estr << "getaddrinfo() failed: " << gai_strerror(rc);
			throw std::runtime_error(estr.str().c_str());
		}

		// create the socket
		if ((sockfd = socket(listener->ai_family, listener->ai_socktype, listener->ai_protocol)) < 0)
		{
			throw std::runtime_error("socket() failed");
		}

		// bind to the socket
		if (bind(sockfd, listener->ai_addr, listener->ai_addrlen) != 0)
		{
			throw std::runtime_error("bind() failed");
		}
		
		// cleanup listener, we are done with it
		freeaddrinfo(listener);
		listener = NULL;
		
		// listen on the socket - allow a backlog of 128
		if (listen(sockfd, 128) != 0)
		{
			throw std::runtime_error("listen() failed");
		}
		
		// get the sockaddr of the listener socket since we called bind with "0"
		struct sockaddr_in sa;
		socklen_t sa_len = sizeof(sa);
		if (getsockname(sockfd, (struct sockaddr*)&sa, &sa_len) != 0)
		{
			throw std::runtime_error("getsockname() failed");
		}
		
		// set the listener socket to be non-blocking
		if (fcntl(sockfd, F_SETFL, O_NONBLOCK) < 0)
		{
			throw std::runtime_error("fcntl() failed");
		}

		// construct socket info strings
		{ std::stringstream ss;
			ss << inet_ntoa(sa.sin_addr);
			address = ss.str();
		}
		{ std::stringstream ss;
			ss << ntohs(sa.sin_port);
			port = ss.str();
		}
	}

	void close() {
		::close(sockfd);
	}

	~Socket() {
		close();
	}

	/*
	  Gah! WTF C++11??? No thread cancelation??????
	  We call select on the sockfd to get around the thread cancelation 
	  problem and waste a few cycles
	  This loops until the main thread detects that the startup barrier has
	  been passed.
	*/
	int accept() {
		fd_set fds;
		struct timeval tv;
		int status;
		struct sockaddr_in wa;
		socklen_t wa_len;
		int wfd;

		// wait up to a second
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		
		while (1) {
			// reset the fd set
			FD_ZERO(&fds);
			FD_SET(sockfd, &fds);
			
			// select on the listener fd
			status = select(sockfd+1, &fds, NULL, NULL, &tv);
			switch (status)
			{
			case -1:
				throw std::runtime_error("select() failed");
					
			case 0:
				/*
				  For an unknown reason there is a different code path
				  for Slurm and Alps where Slurm selects n times for n
				  Valgrinds, but Alps will only select once for many
				  Valgrinds
				*/
				/*
				if(!listener_finish && !finish){
					break;
				}else{
					continue;
					}*/
				continue;
				
			default:
				// need to accept
				break;
			}
			
			
			// accept the new connection
			wa_len = sizeof(wa);
			wfd = ::accept(sockfd, (struct sockaddr*) &wa, &wa_len);
			if (wfd == -1)
			{
				throw std::runtime_error("accept() failed");
			}

			return wfd;
		}
	}

};

#endif