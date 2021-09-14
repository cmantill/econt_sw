#ifndef ECONTRAWDATA
#define ECONTRAWDATA 1

#include <iostream>
#include <deque>

#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/vector.hpp>
#include <boost/thread/thread.hpp>

class ECONTRawData
{
 public:
  ECONTRawData(){;}
  
  ECONTRawData(int event, 
	       std::vector<uint32_t>::const_iterator data_begin,
	       std::vector<uint32_t>::const_iterator data_end);

  int event() const { return m_event; }

  friend std::ostream& operator<<(std::ostream& out,const ECONTRawData& h);

 private:
  friend class boost::serialization::access;
  template<class Archive>
    void serialize(Archive & ar, const unsigned int version)
    {
      ar & m_event;
      ar & m_chip;
      ar & m_data;
    }
  
 private:
  int m_event;
  std::vector<uint32_t> m_data;  
};

class ECONTEventContainer
{
 public:
  ECONTEventContainer();
  ECONTEventContainer(int chip);
  
  void fillContainer( int eventID, const std::vector<uint32_t>& data);

  inline std::deque< std::unique_ptr<ECONTRawData> >& getDequeEvents() {return m_econtdata;} 
  inline void deque_lock(){ m_mutex.lock(); }
  inline void deque_unlock(){ m_mutex.unlock(); }
  
 private:
  std::deque< std::unique_ptr<ECONTRawData> > m_econtdata;
  boost::mutex m_mutex;
  std::vector<uint32_t> m_rawdata;
};

#endif






