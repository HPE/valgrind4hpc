/******************************************************************************\
 * valgrind4hpc_filters.C - MRNet filters for parallel valgrind tool.
 *
 * Copyright 2015,2020 Hewlett Packard Enterprise Development LP..
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 * $HeadURL$
 * $Date$
 * $Rev$
 * $Author$
 *
 ******************************************************************************/

#include <string>
#include <vector>

#include "mrnet/MRNet.h"

#include "valgrind4hpc_protocol.h"

#include "valgrind4hpc_aggregator.h"

const char * ApgrindPairSum_format_string = APG_AGGREGATE_FS;
static void aggregate_packets(const char *format_string, std::vector<MRN::PacketPtr>& packets_in,
                              std::vector<MRN::PacketPtr>& packets_out, std::map<int, FilterAggregator<std::string>*>& counts_map)
{
	if (packets_in.size() == 1)
	{ // no point in trying to aggregate
		packets_out.push_back(packets_in[0]);
		return;
	}
	
	size_t exit_sum = 0;
	int stream_id = packets_in[0]->get_StreamId();
	
	// parse the raw data from packets_in
	
	for (size_t i = 0; i < packets_in.size(); ++i)
	{
		char **val;
		size_t val_len = 0;

		//get the current packet
		MRN::PacketPtr cur_packet = packets_in[i];

		//unpack the current packet
		cur_packet->unpack(format_string, &val, &val_len);

		if (cur_packet->get_Tag() == APG_EXIT)
		{
			for(size_t j = 0; j < val_len; ++j)
			{
				exit_sum += atoi(val[j]);
				free(val[j]);
			}
		} else if (cur_packet->get_Tag() == APG_ERROR) {
			for (size_t j = 0; j < val_len; ++j) {
				std::cerr << "backend exception: " << val[j] << std::endl;
				free(val[j]);
			}
		} else {
			auto count_it = counts_map.find(cur_packet->get_Tag());
			if (count_it == counts_map.end()) {
				throw std::runtime_error(("ApgrindPairSum: Invalid tag! Got " + std::to_string(cur_packet->get_Tag())).c_str());
			}
			FilterAggregator<std::string> *target = count_it->second;

			for(size_t j = 0; j < val_len; ++j)
			{
				std::string msg;
				rank_set_t *ranks_ptr;
				parse_msg(val[j], &msg, &ranks_ptr);
				target->merge(msg, *ranks_ptr);
				free(val[j]);
			}
		}

		free(val);
	}

	// push the parsed packets into packets_out

	for (auto count_it : counts_map)
	{
		int tag = count_it.first;
		Aggregator<std::string> *counts = count_it.second;
		
		char** agg_count = (char**)malloc(counts->size() * sizeof(char*));
		
		int i = 0;
		auto it = counts->begin();
		for (; it != counts->end(); it++)
		{
			std::string msg_str;
			boost::to_string(it->second, msg_str);
			msg_str += " " + it->first;
			agg_count[i] = strdup(msg_str.c_str());
			i++;
		}

		if (counts->size() > 0)
		{
			MRN::PacketPtr new_packet(new MRN::Packet(stream_id,
			                                          tag,
			                                          format_string,
			                                          agg_count,
			                                          counts->size()));
			//new_packet.set_DestroyData(true);
			packets_out.push_back(new_packet);
		}
	}

	// push exit_sum packet if applicable

	if (exit_sum > 0)
	{
		std::string agg_exit_string = std::to_string(exit_sum);
		char **agg_exit_arr = (char**)malloc(sizeof(char*));
		agg_exit_arr[0] = strdup(agg_exit_string.c_str());

		MRN::PacketPtr new_packet(new MRN::Packet(stream_id,
		                                          APG_EXIT,
		                                          ApgrindPairSum_format_string,
		                                          agg_exit_arr,
		                                          1));
		packets_out.push_back(new_packet);
	}
}

extern "C" {

// Format is: 
// "<PE bitset> <rank bitset>... <msg>"
// %as
// TODO: Tag specific filters...

	const char * ApgrindSum_format_string = APG_SUM_FS;
	void ApgrindSum(std::vector< MRN::PacketPtr >& packets_in,
	                std::vector< MRN::PacketPtr >& packets_out,
	                std::vector< MRN::PacketPtr >& /* packets_out_reverse */,
	                void ** /* client data */,
	                MRN::PacketPtr& /* params */,
	                const MRN::TopologyLocalInfo& )
	{
		int sum = 0;
	
		if (packets_in.size() == 1)
		{ // no point in trying to aggregate
			packets_out.push_back(packets_in[0]);
			return;
		}
	
		for (unsigned int i = 0; i < packets_in.size(); ++i)
		{
			MRN::PacketPtr cur_packet = packets_in[i];
			int val;
		
			cur_packet->unpack(ApgrindSum_format_string, &val);
			sum += val;
		}
	
		MRN::PacketPtr new_packet(new MRN::Packet(packets_in[0]->get_StreamId(),
		                                          packets_in[0]->get_Tag(),
		                                          ApgrindSum_format_string,
		                                          sum));
		packets_out.push_back(new_packet);
	}

	void ApgrindPairSum(std::vector< MRN::PacketPtr >& packets_in,
	                    std::vector< MRN::PacketPtr >& packets_out,
	                    std::vector< MRN::PacketPtr >& /* packets_out_reverse */,
	                    void ** /* client data */,
	                    MRN::PacketPtr& /* params */,
	                    const MRN::TopologyLocalInfo& )
	{
		FilterAggregator<std::string> ec, sc;
		std::map<int, FilterAggregator<std::string>*> counts_map = {
			{APG_ERROR_COUNT, &ec},
			{APG_SUPPRESSION_COUNT, &sc}
		};

		aggregate_packets(ApgrindPairSum_format_string, packets_in, packets_out, counts_map);
	}

	const char * ApgrindSummaries_format_string = APG_AGGREGATE_FS;
	void ApgrindSummaries( std::vector< MRN::PacketPtr >& packets_in,
	                       std::vector< MRN::PacketPtr >& packets_out,
	                       std::vector< MRN::PacketPtr >& /* packets_out_reverse */,
	                       void ** /* client data */,
	                       MRN::PacketPtr& /* params */,
	                       const MRN::TopologyLocalInfo& )
	{
		FilterAggregator<std::string> sc;
		std::map<int, FilterAggregator<std::string>*> counts_map = {
			{APG_SUMMARY, &sc}
		};
		
		aggregate_packets(ApgrindSummaries_format_string, packets_in, packets_out, counts_map);
	}

	const char * ApgrindAggregate_format_string = APG_AGGREGATE_FS;
	void ApgrindAggregate(	std::vector< MRN::PacketPtr >& packets_in,
		std::vector< MRN::PacketPtr >& packets_out,
		std::vector< MRN::PacketPtr >& /* packets_out_reverse */,
		void ** /* client data */,
		MRN::PacketPtr& /* params */,
		const MRN::TopologyLocalInfo& )
	{
		FilterAggregator<std::string> mc, ec, errc, suppc;
		std::map<int, FilterAggregator<std::string>*> counts_map = {
			{APG_MSG, &mc},
			{APG_EXIT, &ec},
			{APG_ERROR, &errc},
			{APG_SUPPRESSION, &suppc}
		};
		
		aggregate_packets(ApgrindAggregate_format_string, packets_in, packets_out, counts_map);
	}

	const char * ApgrindLeaks_format_string = APG_AGGREGATE_FS;
	void ApgrindLeaks(	std::vector< MRN::PacketPtr >& packets_in,
		std::vector< MRN::PacketPtr >& packets_out,
		std::vector< MRN::PacketPtr >& /* packets_out_reverse */,
		void ** /* client data */,
		MRN::PacketPtr& /* params */,
		const MRN::TopologyLocalInfo& )
	{
		FilterAggregator<std::string> lc;
		std::map<int, FilterAggregator<std::string>*> counts_map = {
			{APG_LEAK, &lc}
		};

		aggregate_packets(ApgrindLeaks_format_string, packets_in, packets_out, counts_map);
	}
} /* extern "C" */
