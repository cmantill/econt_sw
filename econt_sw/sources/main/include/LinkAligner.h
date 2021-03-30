#ifndef LINK_ALIGNER
#define LINK_ALIGNER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>
#include <zmq.hpp>

#include <FastControlManager.h>
#include <LinkCaptureBlockHandler.h>
#include <IOBlockHandler.h>
#include <eLinkOutputsBlockHandler.h>

class LinkAligner
{
 public:
  LinkAligner(uhal::HwInterface* uhalHWInterface, FastControlManager* fc);
  ~LinkAligner(){;}

  void align();

 private:

 protected:
  uhal::HwInterface* m_uhalHW;
  FastControlManager* m_fcMan;

  eLinkOutputsBlockHandler m_out;
  LinkCaptureBlockHandler m_link_capture;
  IOBlockHandler m_fromIO;
  IOBlockHandler m_toIO;

  std::vector<std::string> m_eLinks;
  std::vector<std::string> m_outputBrams;
};

#endif
