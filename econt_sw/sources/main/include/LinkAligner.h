#ifndef LINK_ALIGNER
#define LINK_ALIGNER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>
#include <zmq.hpp>

#include <FastControlManager.h>
#include <LinkCaptureBlockHandler.h>
#include <IOBlockHandler.h>

#define ALIGN_PATTERN 0xACCCCCCC
#define BX0_PATTERN 0x9CCCCCCC
#define SYNC_WORD 0b00100100010
#define BX0_WORD 0xf922f922
#define NUM_INPUTLINKS 12
#define NUM_OUTPUTLINKS 13

class LinkAligner
{
 public:
  LinkAligner(uhal::HwInterface* uhalHWInterface, FastControlManager* fc);
  ~LinkAligner(){;}

  void align();
  bool checkLinks();

 private:

 protected:
  uhal::HwInterface* m_uhalHW;
  FastControlManager* m_fcMan;

  LinkCaptureBlockHandler m_lchandler;
  IOBlockHandler m_fromIO;
  IOBlockHandler m_toIO;
  std::vector<std::string> m_eLinks;
  std::vector<std::string> m_outputBrams;
};

#endif
