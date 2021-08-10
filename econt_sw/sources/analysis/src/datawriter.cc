#include "datawriter.h"
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>

DelayScanCSVDataWriter::DelayScanCSVDataWriter(std::string aname ) : Writer(aname)
{
  std::cout << "opening " << aname << std::endl;
  ofs.open(aname);
  
  // add header
  ofs << "Link-name" << "," << "iDelay" << "," << "Bits"<< "," <<"Errors" << "\n";
}

DelayScanCSVDataWriter::~DelayScanCSVDataWriter()
{}

void DelayScanCSVDataWriter::fill(link_aligner_data data)
{
  // std::cout << "filling writer name " << m_name << std::endl;
  ofs << data.linkName() << ",";
  ofs << data.delay() << ",";
  ofs << data.bit_counts() << ",";
  ofs << data.error_counts() << "\n";
}

void DelayScanCSVDataWriter::save()
{
  ofs.close();
}
