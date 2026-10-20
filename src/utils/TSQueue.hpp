/******************************************************************************\
 * TSQueue.hpp - Simple threadsafe queue
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

#ifndef _TSQUEUE_HPP
#define _TSQUEUE_HPP

#include <queue>
#include <mutex>
#include <condition_variable>
#include <chrono>

#include <boost/optional.hpp>

template <typename T>
class TSQueue
{
private:
	std::queue<T> q;
	std::mutex m;
	std::condition_variable cv;
	
public:
	TSQueue() { }

	void push(T item)
	{
		std::lock_guard<std::mutex> lck(m);
		q.push(item);
		cv.notify_one();
	}

	template <typename... Us>
	void emplace(Us&&... constructorArgs) {
		std::lock_guard<std::mutex> lck(m);
		q.emplace(std::forward<Us>(constructorArgs)...);
		cv.notify_one();
	}

	T pop()
	{
		std::unique_lock<std::mutex> lck(m);
		while (q.empty())
		{
			cv.wait(lck);
		}
		T item = q.front();
		q.pop();
		return item;
	}

	boost::optional<T> try_pop() {
		std::unique_lock<std::mutex> lck(m);
		while(q.empty()){
			cv.wait_for(lck, std::chrono::duration<double>(0.2));
		}
		if(q.empty()){
			return boost::none;
		}
		T item = q.front();
		q.pop();
		return item;
	}

	bool empty() { return q.empty(); }

	size_t size() { return q.size(); }
	
	TSQueue(const TSQueue&) = delete;
	TSQueue& operator=(const TSQueue&) = delete;
};

#endif