#ifndef ELINKOUTPUTSBLOCKHANDLER
#define ELINKOUTPUSBLOCKHANDLER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>

class eLinkOutputsBlockHandler
{
 public:
  eLinkOutputsBlockHandler(){;}
  eLinkOutputsBlockHandler(uhal::HwInterface* uhalHW,
			   std::string stream_block_name,
			   std::string switch_block_name,
			   std::vector<std::string> bram_names
			   );
  ~eLinkOutputsBlockHandler(){;}

  void setStreamRegister(std::string elink, std::string regName, uint32_t value);
  void setSwitchRegister(std::string elink, std::string regName, uint32_t value);
  void setData(std::string bram_name, std::vector<uint32_t> data, uint32_t size);

 private:
  uhal::HwInterface* m_uhalHW;
  std::string m_stream_block_name;
  std::string m_switch_block_name;
  std::vector<std::string> m_bram_names;
};

#endif
