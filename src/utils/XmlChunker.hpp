/******************************************************************************\
 * XmlChunker.hpp - Utility to split second-level XML blocks from a string
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

#ifndef _XMLCHUNKER_HPP
#define _XMLCHUNKER_HPP

#include <sstream>

/* helper class to extract full XML tags / blocks from an std::istream
	without needing to parse the XML itself. can use to stream second-level
	XML blocks to boost parser instead of waiting for the full XML document */
class XmlChunker {
	// get name of opening tag and index after tag ends
	static std::pair<std::string, size_t> extractOpeningTag(std::string const& chunk) {
		size_t const tagStart = chunk.find("<");
		size_t const tagEnd   = chunk.find(">");

		if ((tagStart == std::string::npos) ||
			(tagEnd   == std::string::npos)) {
			return std::make_pair("", 0);
		}

		auto const openingTag = chunk.substr(tagStart + 1, tagEnd - tagStart - 1);
		return std::make_pair(openingTag, tagEnd + 1);
	}

	// get block of xml as string and index after block ends
	static std::pair<std::string, size_t> extractBlock(std::string const& chunk,
			size_t startSearchAt = 0) {
		// first get the block's tag
		std::string tagName; size_t openTagEnd;
		std::tie(tagName, openTagEnd) = extractOpeningTag(chunk);
		if (tagName.empty()) { return std::make_pair("", 0); }

		// if it's a closing tag, just return the tag
		if (tagName.at(0) == '/') { return std::make_pair(tagName, 0); }

		// find the index of where the closing tag ends
		size_t closeTagStart, closeTagEnd;
		{ std::string closeTag("</" + tagName + ">");
			closeTagStart = chunk.find(closeTag, openTagEnd);
			if (closeTagStart == std::string::npos) {
				return std::make_pair("", 0);
			}
			closeTagEnd = closeTagStart + closeTag.length();
		}
		
		return std::make_pair(
			chunk.substr(0, closeTagEnd),
			closeTagEnd - 1);
	}

	std::istream& instream;
	std::string xmlBuffer;
	size_t restartSearchAt;

public:
	XmlChunker(std::istream& instream_) : instream(instream_) {}

	// read one xml tag from instream
	std::string readTag() {

		// read from the instream until we can get an opening tag
		std::string line;
		while (std::getline(instream, line)) {
			xmlBuffer += line;

			// try to extract a whole tag
			std::string tagName; size_t tagEnd;
			std::tie(tagName, tagEnd) = extractOpeningTag(xmlBuffer);

			if (!tagName.empty()) {
				// remove the tag from the buffer
				xmlBuffer = xmlBuffer.substr(tagEnd);
				return tagName;
			}
		}

		return "";
	}

	// read one xml block from instream
	std::string readBlock() {

		// read from the instream until we can get a full XML block
		std::string line;
		while (instream.good() || !xmlBuffer.empty()) {
			if (std::getline(instream, line)) {
				xmlBuffer += line;
			}

			// try to extract a whole block
			std::string content; size_t possibleEnd;
			std::tie(content, possibleEnd) = extractBlock(xmlBuffer, restartSearchAt);

			if (!content.empty()) {
				// remove the block from the buffer
				xmlBuffer = xmlBuffer.substr(possibleEnd + 1);
				restartSearchAt = 0;
				return content;
			} else {
				if (instream.good()) {
					restartSearchAt = possibleEnd;
				} else {
					// no more input, rest of buffer is malformed
					xmlBuffer.clear();
				}
			}
		}

		return "";
	}

};

#endif