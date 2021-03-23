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

 private:

 protected:
  uhal::HwInterface* m_uhalHW;
  FastControlManager* m_fcMan;
  int m_idelaystep;
  int m_port;

  std::vector<LinkCaptureBlockHandler> m_link_capture_block_handlers;
};

#endif
