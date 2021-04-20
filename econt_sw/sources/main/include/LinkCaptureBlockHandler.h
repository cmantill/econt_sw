#ifndef LINKCAPTUREBLOCKHANDLER
#define LINKCAPTUREBLOCKHANDLER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>

class LinkCaptureBlockHandler
{
 public:
  LinkCaptureBlockHandler(){;}
  LinkCaptureBlockHandler(uhal::HwInterface* uhalHW,
			  std::string link_capture_block_name,
			  std::string bram_name);
  ~LinkCaptureBlockHandler(){;}

  const std::string name() const { return m_link_capture_block_name; }

  void setRegister(std::string elink, std::string regName, uint32_t value);
  void setGlobalRegister(std::string regName, uint32_t value);
  const uint32_t getRegister(std::string elink,std::string regName);
  const uint32_t getGlobalRegister(std::string regName);
  void getData(std::string elink, std::vector<uint32_t> &data, uint32_t size);

 private:
  uhal::HwInterface* m_uhalHW;
  std::string m_link_capture_block_name; //same names as in the address_table/fw_block_addresses.xml file 
  std::string m_bram_name;
};

#endif
