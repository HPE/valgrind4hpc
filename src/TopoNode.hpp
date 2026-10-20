/******************************************************************************\
 * TopoNode.hpp - MRNet topology builder and serializer
 *
 * Copyright 2015-2018,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#ifndef _TOPONODE_HPP
#define _TOPONODE_HPP

// Used when creating topologies
class TopoNode
{
private:
	std::string hostname;
	unsigned int index;
	std::vector<TopoNode*> children;

	void
	PrintNodeTopo( std::ostringstream& ostr, bool recurse )
	{
		// Only print this nodes hostname if we are not recursing through children or this node contains children. 
		// If we are recursing, the parent already added this childs hostname. We only need to specify the topology
		// if this node has children in that case.
		if ( !recurse || !children.empty() ) {
			PrintNodeStr(ostr);
			if ( !children.empty() ) {
				ostr << " =>\n";
			}
		}

		// Print each of the child nodes on their own line
		for ( const auto& i : children ) {
			ostr << "    ";
			i->PrintNodeStr(ostr);
			ostr << '\n';
		}
		
		// add final terminator if we are not calling this method recursively, or this node added children.
		if ( !recurse || !children.empty() ) {
			ostr << "    ;\n";
		}

		// Recurse over each child node.
		for ( const auto& i : children ) {
			i->PrintNodeTopo( ostr, true );
		}
	}

	void
	PrintNodeStr( std::ostringstream& ostr )
	{
		ostr << hostname << ":" << index;
	}

	void
	fixupIndex( std::unordered_map<std::string,unsigned int>& m ) {
		auto e = m.find(hostname);
		if ( e == m.end() ) {
			// First occurance of hostname
			index = 0;
			m[hostname] = 1;
		}
		else {
			index = e->second++;
		}

		for ( auto i : children ) {
			i->fixupIndex( m );
		}
	}

public:
	TopoNode( std::string h )
	: hostname(h), index(0)
	{ }
	
	~TopoNode( void )
	{
		for ( auto i : children ) {
			delete i;
		}
		children.clear();
	}

	std::string getHostname( void ) { return hostname; }

	void
	addChild( TopoNode* child )
	{
		assert( child != nullptr );
		children.push_back(child);
	}

	void
	printTopology( std::ostringstream& ostr )
	{
		// First fixup the indices
		std::unordered_map<std::string,unsigned int> indexLookup;
		// root always has index 0
		index = 0;
		indexLookup[hostname] = 1;

		for ( auto i : children ) {
			i->fixupIndex( indexLookup );
		}

		// Call internal printer method
		PrintNodeTopo( ostr, false );
	}
};

std::string
BuildFlatTopo(unsigned int fanout, std::string myHost, std::set<std::string>& nodes)
{
	std::vector<TopoNode*> currentLevel;
	// Emplace all nodes onto the current level
	for ( const auto& i : nodes ) {
		currentLevel.push_back( new TopoNode(i) );
	}

	do {
		// Create a new level
		std::vector<TopoNode*> newLevel;

		auto nodesOnLevel = currentLevel.size() / fanout;
		// Correct for remainder...
		if ( (currentLevel.size() % fanout) != 0 ) {
			++nodesOnLevel;
		}

		// Create a new root for each of the new comm nodes.
		for ( auto i = 0u; i < nodesOnLevel; ++i ) {
			// If this is the root node, use myHost as the hostname
			TopoNode* newRoot;
			if ( nodesOnLevel == 1 ) {
				newRoot = new TopoNode( myHost );
			}
			else {
				newRoot = new TopoNode( currentLevel[i*fanout]->getHostname() );
			}
			for ( auto j = 0u; j < fanout; ++j ) {
				// Only add this child if it is valid
				if ( (i*fanout + j) < currentLevel.size() ) {
					newRoot->addChild( currentLevel[i*fanout + j] );
				}
				else {
					// Finished processing this level
					break;
				}
			}
			newLevel.push_back( newRoot );
		}

		// Cleanup...
		currentLevel = std::move( newLevel );
	} while( currentLevel.size() > 1 );

	assert( currentLevel.size() == 1 );

	// Turn the resulting topology into a string
	std::ostringstream topologyStr;
	currentLevel[0]->printTopology( topologyStr );
	
	// Done with the TopoNode object
	delete currentLevel[0];
	return topologyStr.str();
}

#endif