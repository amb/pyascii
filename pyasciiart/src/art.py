import pygame
import copy
import sys
import numpy
import os
from processing import Process, Queue

def compare_blocks(ba1, ba2):
    """ Compare two grayscale 2D pixel buffers and calculate their square sum difference """    
    # this is why I love numpy :)
    ba1 = ba1 / (65536)    
    ba2 = ba2 / (65536)
    bares = (ba1 - ba2)**2
    price = numpy.add.reduce(bares.flat)/ba1.shape[0]
            
    return price

class AsciiRenderer:
    """ Generate some nice looking ASCII-art (not necessarily ASCII) """
    def __init__(self, filename):
        
        # load image
        pic = pygame.image.load(filename)
        
        pic_width = pic.get_width()
        pic_height = pic.get_height()
        
        if pic_width>1000 or pic_height>1000:
            print "Error: Image too large (width>1000 or height>1000)"
            return
    
        # Initialise screen
        pygame.init()
        
        # load and init font
        fontfile = pygame.font.match_font('lucida console')
        font = pygame.font.Font(fontfile, 14)

        # list of characters that are used in the creation of the ASCII art
        self.charlist = []
        self.used_encoding = 'latin-1'
        
        # generate character set
        self.fgcolor = (255,255,255)
        self.bgcolor = (0,0,0)
        
        self.max_width = 0
        self.max_height = 0
        self.char_pix = {}
        self.char_rec = {}
        for i in range(33,0xFF):
            try:
                chr(i).encode(self.used_encoding)
            except UnicodeDecodeError:
                continue
            except UnicodeEncodeError:
                continue
    
            if i!=127:
                # init backbuffer
                surf = pygame.Surface((50,50),flags=0)
                surf.fill(self.bgcolor, surf.get_rect())
                
                # get character code
                char = chr(i)
                self.charlist.append(char)
                
                # render character
                text = font.render(char, 1, self.fgcolor)
                rec = text.get_rect()
    
                # background is color (bgcolor)
                surf.fill(self.bgcolor, rec)
                surf.blit(text, rec)
                
                # convert to numpy type array
                self.char_pix[char] = pygame.surfarray.array2d(surf.subsurface(rec))
                self.char_rec[char] = rec
                
                #print char+": "+repr(char_pix[char].shape[0])+"="+repr(rec.width)
                
                # get max dimensions for the character set
                self.max_height = rec.height
                
                if rec.width > self.max_width:
                    self.max_width = rec.width
                
        self.text_height = self.max_height
                    
        print "Max character width: "+repr(self.max_width)
        print "Character height: "+repr(self.max_height)
        
        # convert picture to numpy arrays
        self.num_threads = 4
        pic_arr = pygame.surfarray.array2d(pic)
        
        # split data for threading
        rows = pic_arr.shape[1] / self.text_height  
               
        locs = []
        locs.append(0)
        for i in range(1,self.num_threads):
            locs.append(rows * i / self.num_threads)
        locs.append(rows)
               
        self.thr_arr = []
        for i in range(self.num_threads):
            b_beg = locs[i]  *self.text_height
            b_end = locs[i+1]*self.text_height
            
            self.thr_arr.append(pic_arr[:,b_beg:b_end])
        
    def render(self):
        outstring = ""

        th = [] # Processes
        qs = [] # Message queues
        
        # Init each process
        for i in range(self.num_threads):
            qs.append(Queue())
            th.append(Renderer(self.char_pix, self.text_height, self.max_width, self.thr_arr[i], qs[i]))
            th[i].start()
        
        # Wait for processes to finish
        for thread in th:
            thread.join()
        
        # Read the data from message queues
        for q in qs:
            outstring += q.get()+'\n'
        
        return outstring

        
class Renderer(Process):
    def __init__(self, char_pix, text_height, max_width, pic_arr, q):
        Process.__init__(self)
        self.char_pix = char_pix
        self.text_height = text_height
        self.max_width = max_width
        self.pic_arr = pic_arr
        self.q = q
        self.outstring = ""
        
    def run(self):
        x = 0
        y = 0
        pic_arr = self.pic_arr

        run_loop = True
        # Event loop
        while run_loop:
            # render row
            if x<pic_arr.shape[0] - self.max_width:
                prices = []
                # go through a set of characters to match for fitness
                for (char, text) in self.char_pix.items():         
                    prices.append((compare_blocks(pic_arr[x:x+(text.shape[0]),y:y+(text.shape[1])], text),char))
                
                # i love python  <3
                (best_fit, best_char) = min(prices) 
        
            else:
                if y< (pic_arr.shape[1] - self.text_height*2+1):
                    # new line
                    x = 0
                    y += self.text_height
                    self.outstring += '\n'
                    continue
                    
                    #print "PID:", os.getpid(), "> "+repr(y/self.text_height)+"/"+repr(pic_arr.shape[1]/self.text_height)
                else:
                    # block finished, quit
                    run_loop = False
    
            x += self.char_pix[best_char].shape[0]
            self.outstring += best_char
        
        # Send data to message queue
        self.q.put(self.outstring)

def convert(filename):
    r = AsciiRenderer(filename)

    # calculate render time
    time_start = pygame.time.get_ticks()
    
    ol = r.render()
    print ol

    of = open("ascii_art.txt", "w")
    of.write(ol)
    of.close()        

    print "rendered in: "+repr((pygame.time.get_ticks()-time_start)/1000)+" seconds."

if __name__ == '__main__': 
    if len(sys.argv) == 2:
        convert(sys.argv[1])
    else:
        print "Error: Need exactly one argument: the filename of image"
        
        
