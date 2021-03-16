#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <memory>
#include <algorithm>
#include <iomanip>
#include <signal.h>

#include <unordered_map>
#include <functional>

#include <boost/cstdint.hpp>
#include <boost/program_options.hpp>

#include <uhal/uhal.hpp>

#include "LinkAligner.h"
#include "FastControlManager.h"

int main(int argc,char** argv)
{
  std::string m_connectionfile, m_devicename,m_configFile,m_runtype,m_outFname;
  int m_uhalLogLevel,m_nevent, m_nChip;
  try { 
    /** Define and parse the program options 
     */ 
    namespace po = boost::program_options; 
    po::options_description generic_options("Generic options"); 
    generic_options.add_options()
      ("help,h", "Print help messages")
      ("connectionfile,f", po::value<std::string>(&m_connectionfile)->default_value("address_table/connection.xml"), "name of ipbus connection file")
      ("devicename,d", po::value<std::string>(&m_devicename)->default_value("mylittlememory"), "name of ipbus connection file")
      ("runtype,r", po::value<std::string>(&m_runtype)->default_value("align_links"), "type of run, available options : align_links, find_offset, pedestal, link_alignment_debug")
      ("nevent,N", po::value<int>(&m_nevent)->default_value(1000), "number of events (-1 == run until ctrl-c)")
      ("numberOfRocLinks,n", po::value<int>(&m_nChip)->default_value(12), "number of roc i.e. link blocks")
      ("outFname,o", po::value<std::string>(&m_outFname)->default_value("toto.raw"), "out file name (only used if a file is created. Eg: link_alignment_debug)")
      ("uhalLogLevel,L", po::value<int>(&m_uhalLogLevel)->default_value(4), "uhal log level : 0-Disable; 1-Fatal; 2-Error; 3-Warning; 4-Notice; 5-Info; 6-Debug");


    po::options_description cmdline_options;
    cmdline_options.add(generic_options);

    po::variables_map vm; 
    try { 
      po::store(po::parse_command_line(argc, argv, cmdline_options),  vm); 
      if ( vm.count("help")  ) { 
	std::cout << generic_options   << std::endl; 
        return 0; 
      } 
      po::notify(vm);
    }
    catch(po::error& e) { 
      std::cerr << "ERROR: " << e.what() << std::endl << std::endl; 
      std::cerr << generic_options << std::endl; 
      return 1; 
    }

 
    if( vm.count("connectionfile") ) std::cout << "connectionfile = " << m_connectionfile << std::endl;
    if( vm.count("devicename") )     std::cout << "devicename = "     << m_devicename     << std::endl;
    if( vm.count("runtype")  )       std::cout << "runtype = "        << m_runtype   << std::endl;
    if( vm.count("uhalLogLevel")  )  std::cout << "uhalLogLevel = "   << m_uhalLogLevel   << std::endl;
    std::cout << std::endl;
  }
  catch(std::exception& e) { 
    std::cerr << "Unhandled Exception reached the top of main: " 
              << e.what() << ", application will now exit" << std::endl; 
    return 2; 
  }   

  uhal::ConnectionManager manager( "file://" + m_connectionfile );
  uhal::HwInterface m_ipbushw = manager.getDevice(m_devicename);
  uhal::HwInterface* m_ipbushwptr(&m_ipbushw);

  FastControlManager* fcptr = new FastControlManager( m_ipbushwptr );
  LinkAligner* linkaligner = new LinkAligner( m_ipbushwptr, fcptr );


}
